from __future__ import annotations

from prometheus_client import Counter, Gauge

projects_processed_counter = Counter(
    "projects_processed", "Number of projects that have been processed"
)
tasks_queued_gauge = Gauge("tasks_queued", "Number of tasks currently queued")
worker_exceptions_counter = Counter(
    "worker_exceptions", "Number of exceptions raised by all worker tasks"
)
