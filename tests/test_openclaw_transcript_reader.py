from pathlib import Path
import json

from apps.openclaw_trace_agents.transcript_reader import OpenClawTranscriptReader


def test_openclaw_transcript_reader_extracts_tool_events_from_sample():
    path = Path("data/openclaw_raw/samples/openclaw_session_tool_call_sample.jsonl")

    events = OpenClawTranscriptReader().read_tool_events(path)

    assert [event.tool_name for event in events] == ["exec", "read"]
    assert events[0].arguments == {"command": "cd /workspace && ls"}
    assert events[0].output_summary == "AGENTS.md\nTOOLS.md\nREADME.md"
    assert events[1].arguments["path"] == "/workspace/README.md"


def test_openclaw_transcript_reader_extracts_model_errors(tmp_path):
    path = tmp_path / "session.jsonl"
    records = [
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "provider": "google",
                "model": "gemini-3-pro-preview",
                "stopReason": "error",
                "errorMessage": json.dumps(
                    {
                        "error": {
                            "message": json.dumps(
                                {
                                    "error": {
                                        "message": "This model is no longer available.",
                                    }
                                }
                            )
                        }
                    }
                ),
            },
        }
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    errors = OpenClawTranscriptReader().read_model_errors(path)

    assert errors == ["google/gemini-3-pro-preview: This model is no longer available."]


def test_openclaw_transcript_reader_maps_productivity_exec_calls(tmp_path):
    path = tmp_path / "session.jsonl"
    records = [
        {
            "type": "message",
            "id": "assistant_001",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "toolCall",
                        "id": "call_001",
                        "name": "exec",
                        "arguments": {
                            "command": (
                                "python3 tools/productivity_tool.py gmail_search "
                                '--query "budget review"'
                            )
                        },
                    }
                ],
            },
        },
        {
            "type": "message",
            "message": {
                "role": "toolResult",
                "toolCallId": "call_001",
                "toolName": "exec",
                "details": {"aggregated": "{\"results\": []}"},
            },
        },
    ]
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")

    events = OpenClawTranscriptReader().read_tool_events(path)

    assert events[0].tool_name == "gmail_search"
    assert events[0].arguments["query"] == "budget review"
    assert events[0].arguments["_openclaw_native_tool"] == "exec"
