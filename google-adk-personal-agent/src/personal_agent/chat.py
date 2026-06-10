"""Standalone terminal chat for the independent agent."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from personal_agent.agent import root_agent


async def main() -> None:
    if not os.environ.get("GOOGLE_API_KEY"):
        raise SystemExit("Set GOOGLE_API_KEY in .env.")
    session_id = f"local_{uuid4().hex}"
    user_id = "local_user"
    sessions = InMemorySessionService()
    await sessions.create_session(
        app_name="personal_agent",
        user_id=user_id,
        session_id=session_id,
    )
    runner = Runner(agent=root_agent, app_name="personal_agent", session_service=sessions)
    while True:
        message = input("You: ").strip()
        if not message or message.lower() in {"exit", "quit"}:
            break
        content = types.Content(role="user", parts=[types.Part(text=message)])
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                print(
                    "Agent:",
                    "".join(part.text or "" for part in event.content.parts or []),
                )


if __name__ == "__main__":
    asyncio.run(main())
