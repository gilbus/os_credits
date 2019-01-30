"""
Performs the actual calculations concerning usage and the resulting credit 'billing'
"""

from typing import Dict
from logging import getLogger

from .perun.groupsManager import Group

# (Prometheus) Names of the required measurements
REQUIRED_MEASUREMENTS = {"project_vcpu_usage"}

_logger = getLogger(__name__)


async def process_influx_line(line: str) -> None:
    measurement_and_tag, field_set, timestamp = line.split()
    measurement, tag_set = measurement_and_tag.split(",", 1)
    if measurement not in REQUIRED_MEASUREMENTS:
        _logger.debug(
            "Closed task for line `%s` since its measurement is not needed", line
        )
        return
    _logger.debug("Continuing with line %s", line)
    tags: Dict[str, str] = {}
    for tag_pair in tag_set.split(","):
        tag_name, tag_value = tag_pair.split("=", 1)
        tags.update({tag_name: tag_value})
    perun_group = await Group(tags["project_name"]).connect()
    _logger.info(
        "Got Group (%r) with credits: %s", perun_group, perun_group.denbiCreditsGranted
    )
