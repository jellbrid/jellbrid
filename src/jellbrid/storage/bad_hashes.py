import datetime
from dataclasses import dataclass, field


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass
class BadHash:
    hash: str
    filename: str
    progress: float
    status: str
    created_at: datetime.datetime = field(default_factory=_utc_now)
