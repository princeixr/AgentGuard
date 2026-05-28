"""Run the Google ADK demo path."""

from _bootstrap import bootstrap

bootstrap()
from apps.google_adk_demo_agent.run_demo import main


if __name__ == "__main__":
    main()
