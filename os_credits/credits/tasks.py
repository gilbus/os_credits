"""
Performs the actual calculations concerning usage and the resulting credit 'billing'
"""
from __future__ import annotations

from asyncio import Lock
from dataclasses import replace
from typing import Dict

from aiohttp.web import Application
from os_credits.exceptions import DenbiCreditsCurrentError, GroupNotExistsError
from os_credits.log import TASK_ID, task_logger
from os_credits.perun.groupsManager import Group
from os_credits.prometheus_metrics import worker_exceptions_counter
from os_credits.settings import config

from .base_models import MT
from .billing import calculate_credits
from .models import measurement_by_name


def unique_identifier(influx_line: str) -> str:
    # insert leading zeros if less numbers than 12 but don't use more
    return format(abs(hash(influx_line)), ">012")[:12]


async def worker(name: str, app: Application) -> None:
    group_locks = app["group_locks"]
    task_queue = app["task_queue"]
    while True:
        influx_line: str = await task_queue.get()
        task_id = unique_identifier(influx_line)
        TASK_ID.set(task_id)
        task_logger.debug("Worker %s starting task `%s`", name, task_id)

        try:
            await process_influx_line(influx_line, app, group_locks)
            task_logger.debug(
                "Worker %s finished task `%s` successfully", name, task_id
            )
        except Exception:
            task_logger.exception("%s threw an exception:", name)
        finally:
            task_queue.task_done()


@worker_exceptions_counter.count_exceptions()
async def process_influx_line(
    influx_line: str, app: Application, group_locks: Dict[str, Lock]
) -> None:
    task_logger.debug("Processing Influx Line `%s`", influx_line)
    # we want to end this task as quickly as possible if the InfluxDB Point is not
    # needed
    try:
        measurement_class = measurement_by_name(influx_line)
    except ValueError:
        task_logger.debug("Ignoring since the measurement is not needed/billable")
        return
    try:
        measurement = measurement_class.from_lineprotocol(influx_line)
    except (KeyError, ValueError):
        task_logger.exception(
            "Could not convert influx line %s to UsageMeasurement. Appending stacktrace",
            influx_line,
        )
        return
    perun_group = Group(measurement.project_name, measurement.location_id)
    if "OS_CREDITS_PROJECT_WHITELIST" in config:
        if perun_group.name not in config["OS_CREDITS_PROJECT_WHITELIST"]:
            task_logger.info(
                "Group `%s` is not part of given whitelist (%s). Ignoring measurement",
                perun_group.name,
                config["OS_CREDITS_PROJECT_WHITELIST"],
            )
            return
    task_logger.info(
        "Processing UsageMeasurement `%s` - Group `%s`", measurement, perun_group
    )
    task_logger.debug("Awaiting async lock for Group %s", perun_group.name)
    async with group_locks[perun_group.name]:
        task_logger.debug("Acquired async lock for Group %s", perun_group.name)
        await update_credits(perun_group, measurement, app)


async def update_credits(
    group: Group, current_measurement: MT, app: Application
) -> None:
    try:
        await group.connect()
    except GroupNotExistsError as e:
        task_logger.warning(
            "Could not resolve group with name `%s` against perun. %r", group.name, e
        )
        return
    if group.credits_current.value is None:
        # let's check whether any measurement timestamps are present, if so we are
        # having a problem since this means that this group has been processed before!
        if group.credits_timestamps.value:
            raise DenbiCreditsCurrentError(
                f"Group {group.name} has been billed before but is missing "
                "`credits_current` now. "
                "Did someone modify the values by hand? Aborting"
            )
        else:
            task_logger.info(
                "Group %s does not have `credits_current` and hasn't been billed before: "
                "Copying the value of `credits_granted`",
                group,
            )
            group.credits_current.value = group.credits_granted.value
    try:
        last_measurement_timestamp = group.credits_timestamps.value[
            current_measurement.measurement
        ]
    except KeyError:
        task_logger.info(
            "Group %s has no timestamp of most recent measurement of %s. "
            "Setting it to the timestamp of the current measurement.",
            group,
            current_measurement.measurement,
        )
        # set timestamp of current measurement so we can start billing the group once
        # the next measurements are submitted
        group.credits_timestamps.value[
            current_measurement.measurement
        ] = current_measurement.time
        await group.save()
        return
    task_logger.debug(
        "Last time credits were billed: %s",
        group.credits_timestamps.value[current_measurement.measurement],
    )

    if current_measurement.time < last_measurement_timestamp:
        task_logger.warning(
            "Current measurement is OLDER than the last measurement. HOW? Ignoring"
        )
        return

    project_measurements = await app["influx_client"].previous_measurements(
        measurement=current_measurement, since=last_measurement_timestamp
    )
    try:
        last_measurement = project_measurements[last_measurement_timestamp]
    except KeyError:
        oldest_measurement_timestamp = list(project_measurements)[0]

        group.credits_timestamps.value[
            current_measurement.measurement
        ] = oldest_measurement_timestamp
        task_logger.warning(
            "InfluxDB does not contains usage values for Group %s for measurement %s "
            "at timestamp %s, which means that the period between the last measurement "
            "and now cannot be used for credit billing. Setting the timestamp to the "
            "oldest measurement between now and the last time measurements were billed "
            "inside InfluxDB (%s)",
            group,
            current_measurement.measurement,
            last_measurement_timestamp,
            oldest_measurement_timestamp,
        )
        await group.save()
        return

    credits_to_bill = calculate_credits(current_measurement, last_measurement)
    group.credits_timestamps.value[
        current_measurement.measurement
    ] = current_measurement.time

    previous_group_credits = group.credits_current.value
    group.credits_current.value -= credits_to_bill
    task_logger.info(
        "Credits: %f - %f = %f",
        previous_group_credits,
        credits_to_bill,
        group.credits_current.value,
    )
    await group.save()
