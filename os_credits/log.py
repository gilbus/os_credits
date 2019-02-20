from __future__ import annotations

from contextvars import ContextVar
from logging import Filter, LogRecord, getLogger

TASK_ID: ContextVar[str] = ContextVar("TASK_ID", default="")


class _TaskIdFilter(Filter):
    def filter(self, record: LogRecord) -> bool:
        record.task_id = TASK_ID.get()  # type: ignore
        return True


task_logger = getLogger("os_credits.tasks")
internal_logger = getLogger("os_credits.internal")
requests_logger = getLogger("os_credits.requests")
