"""
Performs the actual calculations concerning usage and the resulting credit 'billing'
"""
from __future__ import annotations

from typing import Dict
from logging import getLogger, LoggerAdapter
from datetime import datetime
from dataclasses import dataclass
from hashlib import sha256 as sha256func

from os_credits.perun.groupsManager import Group
from os_credits.exceptions import GroupNotExistsError
from os_credits.influxdb import InfluxClient
from .measurements import MeasurementType, InfluxMeasurement
from .formulas import calculate_credits


def sha256(content: str) -> str:
    s = sha256func()
    s.update(content.encode())
    return s.hexdigest()


async def process_influx_line(line: str, influx_client: InfluxClient) -> None:
    _debug_logger = getLogger(__name__)
    measurement_and_tag, field_set, timestamp = line.split()
    measurement_name, tag_set = measurement_and_tag.split(",", 1)
    try:
        measurement_type = MeasurementType(measurement_name)
    except ValueError:
        _debug_logger.debug(
            "Closing task for influx line `%s` since its measurement is not"
            " needed/billable",
            line,
        )
        return
    task_identifier = sha256(line)[:12]
    _logger = LoggerAdapter(
        getLogger(f"{__name__}_handler"), {"task_id": task_identifier}
    )
    _logger.debug("Continuing with influx line %s", line)
    measurement_date = datetime.fromtimestamp(int(timestamp) / 1e9)
    tags: Dict[str, str] = {}
    for tag_pair in tag_set.split(","):
        tag_name, tag_value = tag_pair.split("=", 1)
        tags.update({tag_name: tag_value})
    fields: Dict[str, str] = {}
    for field_pair in field_set.split(","):
        field_name, field_value = field_pair.split("=", 1)
        fields.update({field_name: field_value})
    perun_group = Group(tags["project_name"])
    measurement = InfluxMeasurement(
        measurement_date, measurement_type, float(fields["value"])
    )
    _logger.info("Processing Measurement `%s` - Group `%s`", measurement, perun_group)
    try:
        _logger.debug(
            "Awaiting async lock for Group %s to process measurement %s",
            perun_group,
            measurement,
        )
        async with perun_group.async_lock:
            _logger.debug(
                "Acquired async lock for Group %s, measurement %s",
                perun_group,
                measurement,
            )
            await update_credits(perun_group, measurement, influx_client, _logger)
    except GroupNotExistsError as e:
        _logger.warning(
            "Could not resolve group with name `%s` against perun. %r",
            tags["project_name"],
            e,
        )
        return


async def update_credits(
    group: Group, measurement: InfluxMeasurement, influx_client: InfluxClient, _logger
) -> None:
    await group.connect()
    try:
        last_measurement_timestamp = group.credits_timestamps.value[measurement.type]
    except KeyError:
        _logger.info(
            "Group %s has no timestamp of most recent measurement of %s. "
            "Setting it to the timestamp of the current measurement.",
            group,
            measurement.type,
        )
        # set timestamp of current measurement so we can start billing the group once
        # the next measurements are submitted
        group.credits_timestamps.value[measurement.type] = measurement.timestamp
        await group.save()
        return
    _logger.info(
        "Last time credits were billed: %s",
        group.credits_timestamps.value[measurement.type],
    )

    project_measurements = await influx_client.entries_by_project_since(
        group.name, measurement.timestamp, measurement.type
    )
    try:
        last_measurement_value = project_measurements.loc[measurement.timestamp][
            "value"
        ]
    except KeyError:
        _logger.warning(
            """InfluxDB does not contains usage values for Group %s for measurement %s
            at timestamp %s, which means that the period between the last measurement
            and now cannot be used for credit billing. Setting the timestamp to the
            oldest measurement available inside InfluxDB""",
            group,
            measurement.type,
            last_measurement_timestamp,
        )
        group.credits_timestamps.value[measurement.type] = project_measurements.head(1)[
            "value"
        ]
        await group.save()
        return

    _logger.info(
        "Usage value of last measurement: %s",
        project_measurements.loc[measurement.timestamp]["value"],
    )

    credits_to_bill = calculate_credits(measurement, last_measurement_value)
    group.credits_timestamps.value[measurement.type] = measurement.timestamp

    _logger.info("Credits to bill: %f", credits_to_bill)

    group.credits_current.value -= credits_to_bill
    _logger.info("New Group credits %f", group.credits_current.value)
    await group.save()

    # check whether the timestamp inside group is inside the influxdb data
    # if not set timestamp of current measurement and exit, not possible to calculate
    # usage delta
    # if set calculate new credits  and save group
