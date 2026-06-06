"""Run the guarded Google ADK terminal demo."""

import asyncio
import importlib.util

from _bootstrap import bootstrap

bootstrap()

if importlib.util.find_spec("google.adk") is None:
    raise SystemExit(
        "google-adk is not installed in this interpreter. Install the project dependencies "
        "with `uv sync`, then rerun `uv run python scripts/run_google_demo.py`."
    )

from apps.adk_agent.chat import main


if __name__ == "__main__":
    asyncio.run(main())
