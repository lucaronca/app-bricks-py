# Hermes Agent Brick

This Brick runs the [Hermes agent](https://github.com/NousResearch/hermes-agent) (Nous Research) on the board and lets your app expose Python functions as agent **skills**. You chat with the agent through its CLI channel (`docker exec -it <app>-hermes-gateway-1 hermes`) or a messaging platform (Telegram); when the conversation needs one of your skills, the agent calls back into your app and the function runs there — with full access to the Bridge, peripherals, and the other bricks.

## Overview

The Hermes Agent Brick allows you to:

- Register plain Python functions as skills with a one-line decorator
- Chat with an agent that has persistent memory and a built-in scheduler (cron)
- Run fully on-board by default (llamacpp runner on the NPU, no API keys)
- Swap the brain to a cloud provider (`openai:*`, `anthropic:*`, `google:*`) via configuration, like the cloud_llm brick

## How it works

1. The brick adds a companion container (the Hermes **gateway**) to the app compose project and starts a small HTTP **shim** inside the app main container.
2. At boot the gateway polls the shim's `/bootstrap` endpoint, then writes its own configuration (`~/.hermes/config.yaml` + `.env`) and one `SKILL.md` per registered skill (agentskills.io format).
3. During a conversation, when the agent decides to use a skill it executes the instruction in the skill file: an HTTP POST back to the shim, which runs your function and returns its JSON result.
4. Agent state (memory, sessions, self-created skills) persists in `<app>/data/hermes-state/`, so it survives app stop/restart. Skills created by the agent itself are preserved; brick-managed skill files are re-synced at every gateway boot.

## Prerequisites

- Arduino VENTUNO Q (the default model runs on the NPU via the llamacpp service)
- Optional: a Telegram Bot Token from [@BotFather](https://t.me/botfather) in the `TELEGRAM_BOT_TOKEN` variable
- Optional: a cloud provider key in the `API_KEY` variable, only when a cloud model is configured

## Code Example and Usage

`app.yaml`:

```yaml
bricks:
  - arduino:hermes_agent
  # or, with options:
  # - arduino:hermes_agent:
  #     model: openai:gpt-5.2        # cloud override (needs API_KEY)
  #     variables:
  #       TELEGRAM_BOT_TOKEN: "..."
```

`python/main.py`:

```python
from arduino.app_bricks.hermes_agent import HermesAgent
from arduino.app_utils import App, Bridge, Logger

logger = Logger("greenhouse")

hermes = HermesAgent()


@hermes.skill(description="Read the greenhouse temperature in Celsius from the probe wired to the MCU")
def read_greenhouse_temperature() -> float:
    return Bridge.call("read_temperature")


@hermes.skill(description="Report board health: uptime in seconds and available memory in MB")
def get_board_status() -> dict:
    with open("/proc/uptime") as f:
        uptime_seconds = float(f.read().split()[0])
    with open("/proc/meminfo") as f:
        meminfo = dict(line.split(":", 1) for line in f.read().splitlines() if ":" in line)
    available_mb = int(meminfo["MemAvailable"].strip().split()[0]) // 1024
    logger.info(f"Status requested: uptime={uptime_seconds:.0f}s available={available_mb}MB")
    return {"uptime_seconds": uptime_seconds, "available_memory_mb": available_mb}


App.run()
```

Then talk to the agent: *"what's the temperature in the greenhouse?"* — or *"every morning at 8 send me the temperature and the board status"*: scheduling, memory and skill composition are the agent's job, not your code's.

The skill functions run inside the app main container, so anything the app can do (Bridge RPCs, cameras, other bricks) can be a skill. Arguments and return values must be JSON-serializable; the agent reads the `description` to decide when to call, so write it for the model.

## Configuration

| Setting | Default | Notes |
| --- | --- | --- |
| `model` | `llamacpp:gemma-4-E4B_q4_0-it` | Any `llamacpp:*` model, or `openai:*` / `anthropic:*` / `google:*` (needs `API_KEY`) |
| `TELEGRAM_BOT_TOKEN` | unset | Optional; the CLI channel (`docker exec`) works without it |
| `API_KEY` | unset | Cloud provider key, only for cloud models |

## Status — hackathon TODOs

This brick is a scaffold; the mechanics marked TODO need one validation pass against a real Hermes install:

- [ ] Build & push the gateway image (`docker/Dockerfile`); installer URL verified 2026-07-24, release pin still missing
- [ ] Verify `config.yaml` schema keys for the custom provider (base_url/model)
- [x] ~~Webchat port~~ — no web UI exists upstream (README): channels are messaging + CLI; chat via `docker exec ... hermes`
- [ ] Headless Telegram channel wiring (`hermes gateway setup` is interactive)
- [ ] Skills added after gateway boot: verify whether Hermes hot-reloads `~/.hermes/skills/` or needs a gateway restart
- [ ] Sanity-check tool-use quality of the default Gemma 4 E4B q4_0 brain; document a recommended cloud fallback
