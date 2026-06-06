"""Risk and operations routes."""

import csv
import io
import json

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from agentguard.api.dependencies import get_query_service
from agentguard.api.models import OperationsSummary
from agentguard.api.services.query import DashboardQueryService

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/summary", response_model=OperationsSummary)
def summary(
    service: DashboardQueryService = Depends(get_query_service),
) -> OperationsSummary:
    return service.operations()


@router.get("/export")
def export_decisions(
    format: str = "csv",
    service: DashboardQueryService = Depends(get_query_service),
) -> Response:
    records = service.memory(page_size=100).items
    return build_export_response(records, format)


def build_export_response(records, format: str = "csv") -> Response:
    if format == "jsonl":
        content = "".join(
            json.dumps(record.model_dump(mode="json"), separators=(",", ":")) + "\n"
            for record in records
        )
        return Response(
            content=content,
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": 'attachment; filename="agentguard-decisions.jsonl"'
            },
        )
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "timestamp",
            "trace_id",
            "session_id",
            "agent_id",
            "domain",
            "tool_name",
            "risk_score",
            "decision",
            "labels",
            "explanation",
        ],
    )
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "timestamp": record.timestamp.isoformat(),
                "trace_id": record.trace_id,
                "session_id": record.session_id,
                "agent_id": record.agent_id,
                "domain": record.domain,
                "tool_name": record.tool_name,
                "risk_score": record.risk_score,
                "decision": record.decision,
                "labels": "|".join(record.labels),
                "explanation": record.explanation,
            }
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="agentguard-decisions.csv"'},
    )
