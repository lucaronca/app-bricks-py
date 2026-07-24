# Materializes the Hermes configuration and skill files from the bootstrap
# payload served by the HermesAgent brick shim. Runs inside the gateway
# container before `hermes gateway start`. Stdlib only.

import json
import os
import shutil
import sys
from pathlib import Path

# Overridable so the container user/home combination never decides the path.
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
MANAGED_MARKER = "<!-- managed-by: arduino:hermes_agent -->"
LOCAL_DUMMY_API_KEY = "sk-local-no-key"

SKILL_TEMPLATE = """---
name: {name}
description: {description}
---

{marker}

# {name}

{description}

## How to run this skill

Send an HTTP POST to the app container:

```
curl -fsS -X POST -H "Content-Type: application/json" \\
  -d '{{"args": {{{args_example}}}}}' \\
  http://main:{shim_port}/skills/{name}
```

{parameters_section}

The response is JSON: `{{"result": ...}}` on success, `{{"error": "..."}}`
on failure. Report errors to the user instead of retrying blindly.
"""


def write_config(model: dict) -> None:
    """Writes config.yaml (first boot only) and refreshes the managed .env keys."""
    HERMES_HOME.mkdir(parents=True, exist_ok=True)

    config_path = HERMES_HOME / "config.yaml"
    if not config_path.exists():
        # Minimal custom-provider configuration, per Hermes docs.
        # TODO(hackathon): verify the exact config schema keys.
        config_path.write_text(
            "model:\n"
            "  provider: custom\n"
            f"  base_url: \"{model['base_url']}\"\n"
        )
        print(f"Wrote {config_path}")

    if model.get("api_key_source") == "API_KEY":
        api_key = os.environ.get("API_KEY", "").strip()
        if not api_key:
            sys.exit("A cloud model is configured but the API_KEY variable is empty")
    else:
        api_key = LOCAL_DUMMY_API_KEY

    env_path = HERMES_HOME / ".env"
    env: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep:
                env[key.strip()] = value
    env["OPENAI_BASE_URL"] = model["base_url"]
    env["OPENAI_MODEL_NAME"] = model["name"]
    env["OPENAI_API_KEY"] = api_key

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if telegram_token:
        # TODO(hackathon): verify the gateway channel configuration keys
        # (`hermes gateway setup` is interactive; find the headless form).
        env["TELEGRAM_BOT_TOKEN"] = telegram_token
        print("Telegram token found: channel wiring still TODO, see brick README")

    env_path.write_text("".join(f"{key}={value}\n" for key, value in env.items()))
    print(f"Refreshed {env_path}")


def write_skills(skills: list[dict], shim_port: int) -> None:
    """Syncs brick-managed skill folders; agent-created skills are untouched."""
    skills_dir = HERMES_HOME / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)

    wanted = {skill["name"] for skill in skills}
    for existing in skills_dir.iterdir():
        skill_md = existing / "SKILL.md"
        if not existing.is_dir() or not skill_md.exists():
            continue
        if MANAGED_MARKER in skill_md.read_text() and existing.name not in wanted:
            shutil.rmtree(existing)
            print(f"Removed stale managed skill '{existing.name}'")

    for skill in skills:
        parameters = skill.get("parameters", [])
        if parameters:
            lines = [
                f"- `{p['name']}` ({p['type']}, {'required' if p['required'] else 'optional'})"
                for p in parameters
            ]
            parameters_section = "## Arguments\n\n" + "\n".join(lines)
            args_example = ", ".join(f'"{p["name"]}": ...' for p in parameters)
        else:
            parameters_section = "This skill takes no arguments: send `{\"args\": {}}`."
            args_example = ""

        skill_dir = skills_dir / skill["name"]
        skill_dir.mkdir(exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            SKILL_TEMPLATE.format(
                name=skill["name"],
                description=skill["description"],
                marker=MANAGED_MARKER,
                shim_port=shim_port,
                args_example=args_example,
                parameters_section=parameters_section,
            )
        )
        print(f"Wrote skill '{skill['name']}'")


def main() -> None:
    payload = json.loads(Path(sys.argv[1]).read_text())
    write_config(payload["model"])
    write_skills(payload.get("skills", []), payload.get("shim_port", 7181))


if __name__ == "__main__":
    main()
