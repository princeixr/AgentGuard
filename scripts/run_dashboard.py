"""Dashboard runner."""

from _bootstrap import bootstrap

bootstrap()
from agentguard.dashboard.app import run


if __name__ == "__main__":
    run()
