import uuid
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.logging import logger
from backend.app.models.operations import AuditEvent


class AuditService:
    @staticmethod
    async def log_event(
        db: AsyncSession,
        action: str,
        entity_name: str,
        entity_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> AuditEvent:
        """Appends an immutable audit event to the audit trail."""
        event = AuditEvent(
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            actor_user_id=actor_user_id,
            previous_state=previous_state,
            new_state=new_state,
            reason=reason,
            ip_address=ip_address
        )
        db.add(event)
        logger.info(f"AUDIT_EVENT: [{action}] on {entity_name}:{entity_id} by user:{actor_user_id}")
        return event
