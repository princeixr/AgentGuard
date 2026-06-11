"""Database persistence for live runtime records."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from agentguard.server.db.models import ApprovalRecord, RuntimeRecord
from agentguard.server.models import PendingApproval


SessionFactory = Callable[[], Session]


class RuntimeDatabaseStore:
    def __init__(self, session_factory: SessionFactory | None):
        self.session_factory = session_factory

    @property
    def enabled(self) -> bool:
        return self.session_factory is not None

    def save_runtime_record(
        self,
        *,
        record_type: str,
        record_id: str,
        payload: dict[str, Any],
        workspace_id: str | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        if self.session_factory is None:
            return
        now = datetime.now(timezone.utc)
        with self.session_factory() as session:
            bind_name = session.get_bind().dialect.name
            if bind_name == "postgresql":
                statement = pg_insert(RuntimeRecord).values(
                    record_type=record_type,
                    record_id=record_id,
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    payload=payload,
                    created_at=now,
                    updated_at=now,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["record_type", "record_id"],
                    set_={
                        "workspace_id": workspace_id,
                        "agent_id": agent_id,
                        "session_id": session_id,
                        "payload": payload,
                        "updated_at": now,
                    },
                )
                session.execute(statement)
            else:
                existing = session.scalar(
                    select(RuntimeRecord).where(
                        RuntimeRecord.record_type == record_type,
                        RuntimeRecord.record_id == record_id,
                    )
                )
                if existing is None:
                    session.add(
                        RuntimeRecord(
                            record_type=record_type,
                            record_id=record_id,
                            workspace_id=workspace_id,
                            agent_id=agent_id,
                            session_id=session_id,
                            payload=payload,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                else:
                    existing.workspace_id = workspace_id
                    existing.agent_id = agent_id
                    existing.session_id = session_id
                    existing.payload = payload
                    existing.updated_at = now
            session.commit()

    def load_approvals(self) -> dict[str, PendingApproval]:
        if self.session_factory is None:
            return {}
        with self.session_factory() as session:
            rows = session.scalars(select(ApprovalRecord)).all()
            return {
                row.approval_id: PendingApproval.model_validate(row.payload)
                for row in rows
            }

    def save_approval(self, approval: PendingApproval) -> None:
        if self.session_factory is None:
            return
        payload = approval.model_dump(mode="json")
        with self.session_factory() as session:
            existing = session.get(ApprovalRecord, approval.approval_id)
            if existing is None:
                session.add(
                    ApprovalRecord(
                        approval_id=approval.approval_id,
                        decision_id=approval.decision_id,
                        trace_id=approval.trace_id,
                        call_id=approval.call_id,
                        workspace_id=approval.workspace_id,
                        agent_id=approval.agent_id,
                        deployment_id=approval.deployment_id,
                        integration_id=approval.integration_id,
                        session_id=approval.session_id,
                        turn_id=approval.turn_id,
                        tool_name=approval.tool_name,
                        status=approval.status,
                        payload=payload,
                        created_at=approval.created_at,
                        resolved_at=approval.resolved_at,
                        resolved_by=approval.resolved_by,
                        note=approval.note,
                    )
                )
            else:
                existing.status = approval.status
                existing.payload = payload
                existing.resolved_at = approval.resolved_at
                existing.resolved_by = approval.resolved_by
                existing.note = approval.note
            session.commit()
