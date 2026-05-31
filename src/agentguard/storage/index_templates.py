"""Elasticsearch index mappings for AgentGuard v1 records."""

from __future__ import annotations


KEYWORD_IGNORE_ABOVE = 512


def keyword() -> dict:
    return {"type": "keyword", "ignore_above": KEYWORD_IGNORE_ABOVE}


def text_with_keyword() -> dict:
    return {"type": "text", "fields": {"keyword": keyword()}}


TRACE_INDEX_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "trace_id": keyword(),
            "session_id": keyword(),
            "previous_trace_id": keyword(),
            "step_index": {"type": "integer"},
            "@timestamp": {"type": "date"},
            "source": {
                "properties": {
                    "mode": keyword(),
                    "agent_framework": keyword(),
                    "source_type": keyword(),
                    "agent_id": keyword(),
                    "runtime_agent_id": keyword(),
                    "agent_config_id": keyword(),
                    "scenario_id": keyword(),
                    "run_id": keyword(),
                    "environment_id": keyword(),
                }
            },
            "intent": {
                "properties": {
                    "raw_user_request": text_with_keyword(),
                    "normalized_intent": text_with_keyword(),
                    "task_goal": keyword(),
                    "domain": keyword(),
                    "task_category": keyword(),
                    "available_tools": keyword(),
                    "task_relevant_tools": keyword(),
                    "intent_forbidden_tools": keyword(),
                    "confirmation_required_tools": keyword(),
                    "explicit_constraints": {
                        "properties": {
                            "constraint_type": keyword(),
                            "text": text_with_keyword(),
                            "forbidden_tool": keyword(),
                            "forbidden_data_scope": keyword(),
                        }
                    },
                    "allowed_data_scopes": keyword(),
                    "forbidden_data_scopes": keyword(),
                }
            },
            "proposed_tool_call": {
                "properties": {
                    "call_id": keyword(),
                    "tool_name": keyword(),
                    "tool_category": keyword(),
                    "mcp_server": keyword(),
                    "risk_level": keyword(),
                    "side_effect_type": keyword(),
                    "arguments": {"type": "flattened"},
                    "argument_summary": text_with_keyword(),
                    "argument_hash": keyword(),
                }
            },
            "trajectory": {
                "properties": {
                    "prior_tool_names": keyword(),
                    "prior_tool_sequence": text_with_keyword(),
                    "prior_tool_count": {"type": "integer"},
                    "previous_tool_name": keyword(),
                    "previous_output_summary": {"type": "text", "index": False},
                    "prior_side_effect_count": {"type": "integer"},
                    "prior_blocked_count": {"type": "integer"},
                    "prior_approval_required_count": {"type": "integer"},
                }
            },
            "tool_output_context": {
                "properties": {
                    "contains_untrusted_instruction": {"type": "boolean"},
                    "contains_external_link": {"type": "boolean"},
                    "contains_secret_like_content": {"type": "boolean"},
                    "output_influenced_current_call": {"type": "boolean"},
                }
            },
            "retrieval_text": {
                "properties": {
                    "summary": {"type": "text"},
                    "intent_text": {"type": "text"},
                    "trajectory_text": {"type": "text"},
                    "argument_text": {"type": "text"},
                }
            },
            "execution": {
                "properties": {
                    "status": keyword(),
                    "executed_at": {"type": "date"},
                    "latency_ms": {"type": "integer"},
                    "output_summary": {"type": "text", "index": False},
                    "output_ref": keyword(),
                }
            },
        },
    },
}


LIVE_EVENT_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "event_id": keyword(),
            "@timestamp": {"type": "date"},
            "event_type": keyword(),
            "trace_id": keyword(),
            "session_id": keyword(),
            "step_index": {"type": "integer"},
            "agent_framework": keyword(),
            "agent_id": keyword(),
            "payload": {"type": "flattened"},
        },
    },
}


TRACE_FEATURE_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "feature_id": keyword(),
            "trace_id": keyword(),
            "session_id": keyword(),
            "step_index": {"type": "integer"},
            "@timestamp": {"type": "date"},
            "retrieval": {
                "properties": {
                    "query_text": {"type": "text"},
                    "top_k": {"type": "integer"},
                    "approved_trace_ids": keyword(),
                    "blocked_trace_ids": keyword(),
                    "max_approved_similarity": {"type": "float"},
                    "max_blocked_similarity": {"type": "float"},
                    "mean_approved_similarity": {"type": "float"},
                    "mean_blocked_similarity": {"type": "float"},
                    "blocked_neighbor_ratio": {"type": "float"},
                }
            },
        },
    },
}


GUARD_SCORE_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "score_id": keyword(),
            "trace_id": keyword(),
            "feature_id": keyword(),
            "session_id": keyword(),
            "step_index": {"type": "integer"},
            "guard_version": keyword(),
            "@timestamp": {"type": "date"},
        },
    },
}


GUARD_DECISION_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "decision_id": keyword(),
            "trace_id": keyword(),
            "score_id": keyword(),
            "session_id": keyword(),
            "step_index": {"type": "integer"},
            "@timestamp": {"type": "date"},
            "decision": keyword(),
            "tier_used": keyword(),
            "final_risk_score": {"type": "float"},
            "decision_rules_fired": keyword(),
            "explanation": {"type": "text"},
            "latency_ms": {"type": "integer"},
        },
    },
}


SESSION_RISK_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "session_id": keyword(),
            "agent_framework": keyword(),
            "agent_id": keyword(),
            "last_trace_id": keyword(),
            "last_score_id": keyword(),
            "last_step_index": {"type": "integer"},
            "updated_at": {"type": "date"},
            "tool_sequence": keyword(),
            "max_single_step_risk": {"type": "float"},
        },
    },
}


LABEL_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "label_id": keyword(),
            "trace_id": keyword(),
            "labeler_id": keyword(),
            "@timestamp": {"type": "date"},
            "gold_verdict": keyword(),
            "failure_type": keyword(),
            "label_confidence": keyword(),
            "rationale_summary": {"type": "text"},
        },
    },
}


SCENARIO_INDEX_MAPPING = {
    "mappings": {
        "dynamic": True,
        "properties": {
            "schema_version": keyword(),
            "scenario_id": keyword(),
            "domain": keyword(),
            "task_category": keyword(),
            "user_request": {"type": "text"},
            "expected_allowed_tools": keyword(),
            "expected_disallowed_tools": keyword(),
            "expected_constraints": keyword(),
            "failure_type": keyword(),
            "agent_behavior_mode": keyword(),
            "gold_final_verdict": keyword(),
        },
    },
}


def all_index_mappings(index_names) -> dict[str, dict]:
    return {
        index_names.traces: TRACE_INDEX_MAPPING,
        index_names.live_events: LIVE_EVENT_INDEX_MAPPING,
        index_names.trace_features: TRACE_FEATURE_INDEX_MAPPING,
        index_names.guard_scores: GUARD_SCORE_INDEX_MAPPING,
        index_names.guard_decisions: GUARD_DECISION_INDEX_MAPPING,
        index_names.session_risk: SESSION_RISK_INDEX_MAPPING,
        index_names.labels: LABEL_INDEX_MAPPING,
        index_names.scenarios: SCENARIO_INDEX_MAPPING,
    }
