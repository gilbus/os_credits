"""
Performs the actual calculations concerning usage and the resulting credit 'billing'
"""
from __future__ import annotations

from typing import Dict
from logging import getLogger
from datetime import datetime

from .perun.groupsManager import Group
from .perun.requests import GroupNotExists
from .influxdb import InfluxClient
from .measurements import Measurement

_logger = getLogger(__name__)


async def process_influx_line(line: str, influx_client: InfluxClient) -> None:
    measurement_and_tag, field_set, timestamp = line.split()
    measurement_name, tag_set = measurement_and_tag.split(",", 1)
    try:
        measurement_type = Measurement(measurement_name)
    except ValueError:
        _logger.debug(
            "Closing task for influx line `%s` since its measurement is not"
            " needed/billable",
            line,
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
    except GroupNotExists as e:
        _logger.warning(
            "Could not resolve group with name `%s` against perun. %r",
            tags["project_name"],
            e,
        )
        return

    try:
        last_measurement_timestamp = perun_group.credits_timestamps.value[
            measurement_type
        ]
    except KeyError:
        _logger.info(
            "Group %s has no value for denbiCreditsTimestamp, setting timestamp of last "
            "this measurement",
            perun_group,
        )

    if not perun_group.credits_timestamps.value[measurement_type]:
        # this group has never been billed before, meaning there are no previous
        # measurements
        _logger.info(
            "Group %s has no value for denbiCreditsTimestamp, setting timestamp of last "
            "this measurement",
            perun_group,
        )
        # set timestamp of current measurement so we can start billing the group once
        # the next measurements are submitted
        perun_group.credits_timestamp.value = measurement_date
        await perun_group.save()
        return
    _logger.info(
        "Last time credits were billed: %s", perun_group.credits_timestamp.value
    )

    project_measurements = await influx_client.entries_by_project_since(
        tags["project_name"], measurement_date
    )

    _logger.info(
        "Usage value of last measurement: %s",
        project_measurements.loc[measurement_date]["value"],
    )

    # check whether the timestamp inside group is inside the influxdb data
    # if not set timestamp of current measurement and exit, not possible to calculate
    # usage delta
    # if set calculate new credits  and save group
