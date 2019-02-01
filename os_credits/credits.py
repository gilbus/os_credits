"""
Performs the actual calculations concerning usage and the resulting credit 'billing'
"""
from __future__ import annotations

from typing import Dict
from logging import getLogger
from datetime import datetime

from .perun.groupsManager import Group
from .perun.requests import GroupNotExistsError
from .influxdb import InfluxClient

# (Prometheus) Names of the required measurements
REQUIRED_MEASUREMENTS = {"project_vcpu_usage"}

_logger = getLogger(__name__)


async def process_influx_line(line: str, influx_client: InfluxClient) -> None:
    measurement_and_tag, field_set, timestamp = line.split()
    measurement, tag_set = measurement_and_tag.split(",", 1)
    if measurement not in REQUIRED_MEASUREMENTS:
        _logger.debug(
            "Closed task for influx line `%s` since its measurement is not needed", line
        )
        return
    _logger.debug("Continuing with influx line %s", line)
    _logger.info("Timestamp %s", timestamp)
    measurement_date = datetime.fromtimestamp(int(timestamp) / 1e9)
    tags: Dict[str, str] = {}
    for tag_pair in tag_set.split(","):
        tag_name, tag_value = tag_pair.split("=", 1)
        tags.update({tag_name: tag_value})
    try:
        perun_group = await Group(tags["project_name"]).connect()
    except GroupNotExistsError as e:
        _logger.warning(
            "Could not resolve group with name `%s` against perun. %r",
            tags["project_name"],
            e,
        )
        return

    _logger.info(
        "Last time credits were billed: %s",
        perun_group.denbiCreditsCurrent.valueModifiedAt,
    )
    project_measurements = await influx_client.entries_by_project_since(
        tags["project_name"], measurement_date
    )
    _logger.info(project_measurements.loc[measurement_date])


async def calculate(last_timestamp: datetime):
    pass
