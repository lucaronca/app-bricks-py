# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

import inspect
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

from arduino.app_utils import Logger, brick
from arduino.app_internal.core import get_brick_config, get_brick_configured_model

logger = Logger("HermesAgent")

# Same resolution the llm brick applies: "llamacpp:<name>" runs on the on-board
# runner and the server-side model name is the string without the prefix.
LLAMACPP_RUNNER_BASE_URL = "http://llamacpp-models-runner:9999/v1"
LLAMACPP_MODEL_PREFIX = "llamacpp"

# OpenAI-compatible endpoints for the cloud providers supported by cloud_llm.
# TODO(hackathon): verify the anthropic OpenAI-compatibility endpoint coverage.
CLOUD_OPENAI_COMPATIBLE_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta/openai",
    "anthropic": "https://api.anthropic.com/v1",
}

DEFAULT_SHIM_PORT = 7181


class _ShimServer(ThreadingHTTPServer):
    """HTTP server carrying a reference to the owning HermesAgent brick."""

    daemon_threads = True
    hermes_brick: "HermesAgent"


class _ShimRequestHandler(BaseHTTPRequestHandler):
    """Serves the bootstrap payload and executes registered skills.

    Routes:
        GET  /bootstrap        -> model endpoint configuration + skills manifest
        POST /skills/<name>    -> run the skill; body: {"args": {...}} (optional)
    """

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug(f"shim: {format % args}")

    def _reply(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/bootstrap":
            self._reply(200, self.server.hermes_brick.bootstrap_payload())
            return
        self._reply(404, {"error": f"unknown path: {self.path}"})

    def do_POST(self) -> None:
        if not self.path.startswith("/skills/"):
            self._reply(404, {"error": f"unknown path: {self.path}"})
            return
        skill_name = self.path[len("/skills/"):].strip("/")

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length) if content_length else b"{}"
            args = json.loads(raw_body or b"{}").get("args", {})
            if not isinstance(args, dict):
                raise ValueError("'args' must be a JSON object")
        except (ValueError, json.JSONDecodeError) as e:
            self._reply(400, {"error": f"invalid request body: {e}"})
            return

        try:
            result = self.server.hermes_brick.run_skill(skill_name, args)
        except KeyError:
            self._reply(404, {"error": f"unknown skill: {skill_name}"})
            return
        except TypeError as e:
            # Signature mismatch (wrong/missing arguments from the agent)
            self._reply(400, {"error": f"invalid arguments for '{skill_name}': {e}"})
            return
        except Exception as e:
            logger.exception(f"Skill '{skill_name}' failed")
            self._reply(500, {"error": f"skill '{skill_name}' raised: {e}"})
            return

        self._reply(200, {"result": result})


@brick
class HermesAgent:
    """Exposes your app's Python functions as skills of a Hermes agent.

    The Hermes gateway (Nous Research agent) runs in a companion container
    defined by this brick's compose file. At startup the gateway pulls a
    bootstrap payload from this brick (model endpoint + skills manifest),
    materializes its configuration and skill files, then connects to its
    chat channels. When a conversation needs one of your skills, the
    gateway calls back into this brick over HTTP and the decorated
    function runs inside the app main container.

    The model is resolved like the llm/cloud_llm bricks:
      - "llamacpp:<name>"  -> on-board runner on the NPU (default)
      - "openai:<name>", "anthropic:<name>", "google:<name>" -> cloud
        provider through its OpenAI-compatible endpoint (requires the
        API_KEY brick variable)
    """

    def __init__(self, model: Optional[str] = None, shim_port: int = DEFAULT_SHIM_PORT):
        """Initializes the HermesAgent brick.

        Args:
            model (Optional[str]): Model identifier (e.g. "llamacpp:gemma-4-E4B_q4_0-it"
                or "openai:gpt-5.2"). If not provided, it is resolved from the app
                configuration or the brick default.
            shim_port (int): Port of the internal HTTP shim the gateway calls
                back into. Must match HERMES_BOOTSTRAP_URL in the compose file.
        """
        self._skills: dict[str, dict] = {}
        self._shim_port = shim_port
        self._server: Optional[_ShimServer] = None
        self._model = model or self._configured_model()
        # Fail fast on unsupported model strings instead of at gateway boot.
        self._endpoint = self._resolve_model_endpoint(self._model)
        logger.info(f"Agent brain: '{self._model}' via {self._endpoint['base_url']}")

    def skill(self, description: str, name: Optional[str] = None) -> Callable:
        """Registers a function as a skill the agent can use.

        The description is what the agent reads to decide when to use the
        skill — write it for the model, not for humans. Arguments and return
        value must be JSON-serializable.

        Args:
            description (str): What the skill does, from the agent's point of view.
            name (Optional[str]): Skill name; defaults to the function name.

        Returns:
            The decorator that registers the function (returned unchanged).
        """
        if not description or not description.strip():
            raise ValueError("A skill needs a non-empty description")

        def decorator(fn: Callable) -> Callable:
            skill_name = name or fn.__name__
            if skill_name in self._skills:
                raise ValueError(f"Skill '{skill_name}' is already registered")
            self._skills[skill_name] = {
                "fn": fn,
                "description": description.strip(),
                "parameters": self._describe_parameters(fn),
            }
            logger.info(f"Registered skill '{skill_name}'")
            return fn

        return decorator

    def run_skill(self, name: str, args: dict) -> Any:
        """Runs a registered skill by name. Raises KeyError if unknown."""
        entry = self._skills[name]
        logger.info(f"Agent invoked skill '{name}' with args {args}")
        return entry["fn"](**args)

    def bootstrap_payload(self) -> dict:
        """Payload the gateway container pulls at boot to configure itself."""
        return {
            "model": {
                "base_url": self._endpoint["base_url"],
                "name": self._endpoint["model_name"],
                # The gateway resolves the actual secret from its own
                # environment (API_KEY variable); secrets never transit here.
                "api_key_source": self._endpoint["api_key_source"],
            },
            "shim_port": self._shim_port,
            "skills": [
                {
                    "name": skill_name,
                    "description": entry["description"],
                    "parameters": entry["parameters"],
                }
                for skill_name, entry in self._skills.items()
            ],
        }

    @brick.execute
    def serve_shim(self) -> None:
        """Serves the bootstrap payload and skill calls (runs in a brick thread)."""
        self._server = _ShimServer(("0.0.0.0", self._shim_port), _ShimRequestHandler)
        self._server.hermes_brick = self
        logger.info(f"Skill shim listening on :{self._shim_port} ({len(self._skills)} skills)")
        self._server.serve_forever()

    def stop(self) -> None:
        """Stops the shim server."""
        if self._server:
            self._server.shutdown()
            self._server = None

    def _configured_model(self) -> str:
        """Resolves the model from app configuration or the brick default."""
        brick_config = get_brick_config(self.__class__)
        configured = get_brick_configured_model(
            brick_config.get("id") if brick_config else None, brick_config=brick_config
        )
        if configured:
            logger.info(f"Using configured model: '{configured}'")
            return configured
        default = (brick_config or {}).get("model")
        if not default:
            raise ValueError("No model configured for the hermes_agent brick")
        logger.info(f"Using default model: '{default}'")
        return default

    @staticmethod
    def _resolve_model_endpoint(model: str) -> dict:
        """Maps a "provider:name" model string to an OpenAI-compatible endpoint."""
        provider, _, model_name = model.partition(":")
        if not model_name:
            raise ValueError(f"Model '{model}' must be in '<provider>:<name>' form")
        if provider == LLAMACPP_MODEL_PREFIX:
            return {
                "base_url": LLAMACPP_RUNNER_BASE_URL,
                "model_name": model_name,
                "api_key_source": "none",  # runner accepts any key
            }
        if provider in CLOUD_OPENAI_COMPATIBLE_BASE_URLS:
            return {
                "base_url": CLOUD_OPENAI_COMPATIBLE_BASE_URLS[provider],
                "model_name": model_name,
                "api_key_source": "API_KEY",
            }
        raise ValueError(
            f"Unsupported model provider '{provider}'. "
            f"Use 'llamacpp:*' or one of: {', '.join(CLOUD_OPENAI_COMPATIBLE_BASE_URLS)}"
        )

    @staticmethod
    def _describe_parameters(fn: Callable) -> list[dict]:
        """Extracts a JSON-friendly parameter manifest from the function signature."""
        parameters = []
        for param in inspect.signature(fn).parameters.values():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            annotation = (
                param.annotation.__name__
                if inspect.isclass(param.annotation)
                else str(param.annotation)
            )
            parameters.append(
                {
                    "name": param.name,
                    "type": annotation if param.annotation is not param.empty else "any",
                    "required": param.default is param.empty,
                }
            )
        return parameters
