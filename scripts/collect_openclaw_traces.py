"""Collect OpenClaw traces for research benchmarking."""

from _bootstrap import bootstrap

bootstrap()
from apps.openclaw_trace_agents.run_trace_collection import main


if __name__ == "__main__":
    main()
