from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from common.kernel.types import OpId, ShopId


@dataclass(frozen=True, slots=True)
class DomainEventOutbox:
    shop_id: ShopId
    op_id: OpId
    event_type: str
    payload: dict
    payload_hash: str
    idempotency_key: str
    created_at: datetime
    processed_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        shop_id: ShopId,
        op_id: OpId,
        event_type: str,
        payload: dict,
        payload_hash: str,
        idempotency_key: str,
    ) -> "DomainEventOutbox":
        return cls(
            shop_id=shop_id,
            op_id=op_id,
            event_type=event_type,
            payload=payload,
            payload_hash=payload_hash,
            idempotency_key=idempotency_key,
            created_at=datetime.now(),
        )
