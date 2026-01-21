# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

from arduino.app_bricks.cloud_llm import CloudLLM, CloudModelProvider
from arduino.app_utils import Logger, brick
import os
from typing import Iterator, List, Optional, Union, Any, Callable


@brick
class LocalLLM(CloudLLM):
    """A Brick for interacting with locally-based Large Language Models (LLMs).

    This class wraps LangChain functionality to provide a simplified, unified interface
    for chatting with models like Qwenm, LLama, Gemma. It supports both synchronous
    'one-shot' responses and streaming output, with optional conversational memory.
    """

    def __init__(
        self,
        api_key: str = os.getenv("API_KEY", ""),
        model: str = "qwen2.5-7b",
        system_prompt: str = "",
        temperature: Optional[float] = 0.7,
        timeout: int = 30,
        tools: List[Callable[..., Any]] = None,
        **kwargs,
    ):
        """Initializes the CloudLLM brick with the specified provider and configuration.

        Args:
            api_key (str): The API access key for the target LLM service. Defaults to the
                'API_KEY' environment variable.
            model (str): The specific model name or identifier to use (e.g., "gpt-4").
            system_prompt (str): A system-level instruction that defines the AI's persona
                and constraints (e.g., "You are a helpful assistant"). Defaults to empty.
            temperature (Optional[float]): The sampling temperature between 0.0 and 1.0.
                Higher values make output more random/creative; lower values make it more
                deterministic. Defaults to 0.7.
            timeout (int): The maximum duration in seconds to wait for a response before
                timing out. Defaults to 30.
            tools (List[Callable[..., Any]]): A list of callable tool functions to register. Defaults to None.
            **kwargs: Additional arguments passed to the model constructor

        Raises:
            ValueError: If `api_key` is not provided (empty string).
        """

        # TODO configure URL to point to proper service endpoint
        # base_url = 'http://localhost:11434/v1',

        host = "localhost"
        port = 11434

        base_url = f"http://{host}:{port}/v1"

        # Force OpenAI provider for local LLMs to force ChatCompletion APIs
        model = f"{CloudModelProvider.OPENAI}:{model}"

        super().__init__(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            timeout=timeout,
            tools=tools,
            base_url=base_url,
            **kwargs,
        )
