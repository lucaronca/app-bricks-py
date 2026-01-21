# SPDX-FileCopyrightText: Copyright (C) ARDUINO SRL (http://www.arduino.cc)
#
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from conftest import ModelConfig
from arduino.app_bricks.cloud_llm import CloudLLM
from stubs.weather_tool import get_current_weather
from runners import runner, ToolTrace


def _run(
    model: ModelConfig,
    prompt: str,
    port: int,
    tool_trace: ToolTrace,
    tools: Optional[List[Any]] = None,
) -> Tuple[CloudLLM, str]:
    llm_kwargs: Dict[str, Any] = {
        "model": model.name,
        "temperature": 0,
        "api_key": model.api_key,
        "mcp_servers": [
            {
                "name": "home_automation",
                "connection": {
                    "transport": "streamable_http",
                    "url": f"http://localhost:{port}/mcp",
                },
            }
        ],
        "callbacks": [tool_trace],
    }

    if tools:
        llm_kwargs["tools"] = tools

    llm = CloudLLM(**llm_kwargs)
    llm_response = llm.chat(prompt)

    return llm, llm_response


@runner
def run_granular(model: ModelConfig, prompt: str, tool_trace: ToolTrace) -> Tuple[CloudLLM, str]:
    return _run(model=model, prompt=prompt, port=8000, tool_trace=tool_trace)


@runner
def run_granular_with_weather(model: ModelConfig, prompt: str, tool_trace: ToolTrace) -> Tuple[CloudLLM, str]:
    return _run(model=model, prompt=prompt, port=8000, tools=[get_current_weather], tool_trace=tool_trace)


@runner
def run_object(model: ModelConfig, prompt: str, tool_trace: ToolTrace) -> Tuple[CloudLLM, str]:
    return _run(model=model, prompt=prompt, port=8001, tool_trace=tool_trace)


@runner
def run_object_with_weather(model: ModelConfig, prompt: str, tool_trace: ToolTrace) -> Tuple[CloudLLM, str]:
    return _run(model=model, prompt=prompt, port=8001, tools=[get_current_weather], tool_trace=tool_trace)
