"""
Contains test which launch the whole application and simulate incoming data or external
requests against it. They all require the aiohttp_client and influx_client fixture, the
latter even if they do not the InfluxDB functionality since the app does check the
existence of certain databases at startup.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from importlib import reload
from typing import Type

from pytest import fixture

import os_credits.perun.attributesManager
import os_credits.perun.group
from os_credits.credits.models import BillingHistory

from . import patches
from .patches import (
    get_attributes,
    get_group_by_name,
    get_resource_bound_attributes,
    is_assigned_resource,
    set_attributes,
    set_resource_bound_attributes,
)


@fixture
def os_credits_offline(monkeypatch):
    """Applies patches to emulate *Perun* offline. Online tests are done in test_perun.
    """

    monkeypatch.setattr(
        os_credits.perun.group,
        "get_resource_bound_attributes",
        get_resource_bound_attributes,
    )
    monkeypatch.setattr(
        os_credits.perun.group,
        "set_resource_bound_attributes",
        set_resource_bound_attributes,
    )
    monkeypatch.setattr(os_credits.perun.group, "get_attributes", get_attributes)
    monkeypatch.setattr(os_credits.perun.group, "set_attributes", set_attributes)
    monkeypatch.setattr(
        os_credits.perun.group.Group, "is_assigned_resource", is_assigned_resource
    )
    monkeypatch.setattr(os_credits.perun.group.Group.save, "__defaults__", (True,))

    monkeypatch.setattr(os_credits.perun.group, "get_group_by_name", get_group_by_name)
    yield
    # reset internal storage of group values by reloading the module
    reload(patches)


@fixture(name="start_date")
def fixture_start_date():
    return datetime(2019, 1, 1)


@fixture(name="usage_delta")
def fixture_usage_delta():
    return 5


@fixture(name="MeasurementClass", scope="session")
def fixture_measurement_class():
    from os_credits.credits.base_models import (
        Metric,
        TotalUsageMetric,
        UsageMeasurement,
    )

    test_metric_name = "whole_run_test_1"

    class _TestMetric(
        TotalUsageMetric, name=test_metric_name, friendly_name=test_metric_name
    ):
        CREDITS_PER_VIRTUAL_HOUR = Decimal("1")
        description = "Test Metric 1 for whole run test"

    @dataclass(frozen=True)
    class _TestMeasurement(UsageMeasurement):
        metric: Type[Metric] = _TestMetric

    return _TestMeasurement


@fixture
async def app_with_first_write(
    aiohttp_client,
    os_credits_offline,
    influx_client,
    perun_test_group,
    MeasurementClass,
    start_date,
):
    from os_credits.main import create_app

    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)

    measurement = MeasurementClass(
        measurement=MeasurementClass.metric.name,
        timestamp=start_date,
        location_id=perun_test_group.resource_id,
        project_name=perun_test_group.name,
        value=100,
    )

    await write_and_mirror(app, http_client, influx_client, measurement)
    await perun_test_group.connect()
    assert (
        perun_test_group.credits_used.value == 0
    ), "Initial value of credits_used was not set"
    assert (
        perun_test_group.credits_timestamps.value[measurement.measurement] == start_date
    ), "Timestamp from measurement was not stored correctly in group"
    return app, http_client, influx_client, measurement


async def write_and_mirror(app, http_client, influx_client, measurement):
    # async def write_and_mirror(http_client, influx_client, measurement):
    if influx_client:
        await influx_client.write(measurement)
    resp = await http_client.post("/write", data=measurement.to_lineprotocol())
    assert resp.status == 202
    # wait until request has been processed, indicated by the task finally calling
    # `task_done`
    await app["task_queue"].join()


async def get_billing_history(perun_test_group, influx_client):
    return [
        p
        async for p in await influx_client.query_billing_history(perun_test_group.name)
    ]


async def test_startup(aiohttp_client, influx_client):
    "Test startup of the application and try to connect to its `/ping` endpoint"
    from os_credits.main import create_app

    app = await create_app(_existing_influxdb_client=influx_client)
    client = await aiohttp_client(app)
    resp = await client.get("/ping")
    text = await resp.text()
    assert (200, "Pong") == (resp.status, text), "/ping endpoint failed"


async def test_credits_endpoint(aiohttp_client, influx_client):
    """Test the `get_metrics` endpoint responsible for calculating expected costs per
    hour of given resources"""
    from os_credits.main import create_app
    from os_credits.credits.base_models import TotalUsageMetric

    app = await create_app(_existing_influxdb_client=influx_client)
    client = await aiohttp_client(app)

    class _MetricA(TotalUsageMetric, name="metric_a", friendly_name="metric_a"):
        CREDITS_PER_VIRTUAL_HOUR = Decimal("1.3")
        description = "Test metric A"

        @classmethod
        def api_information(cls):
            return {
                "type": "str",
                "description": cls.description,
                "name": cls.name,
                "friendly_name": cls.friendly_name,
            }

    class _MetricB(TotalUsageMetric, name="metric_b", friendly_name="metric_b"):
        CREDITS_PER_VIRTUAL_HOUR = Decimal("1")
        description = "Test metric B"

    get_metrics_url = app.router["get_metrics"].url_for()
    resp = await client.get(get_metrics_url)
    metrics = await resp.json()
    assert resp.status == 200
    assert metrics["metric_a"] == {
        "description": "Test metric A",
        "type": "str",
        "name": "metric_a",
        "friendly_name": "metric_a",
    }, "Returned wrong body"
    assert metrics["metric_b"] == {
        "description": "Test metric B",
        "type": "int",
        "name": "metric_b",
        "friendly_name": "metric_b",
    }, "Returned wrong body"

    costs_per_hour_url = app.router["costs_per_hour"].url_for()
    resp = await client.post(costs_per_hour_url, json={"DefinitelyNotExisting": "test"})
    assert resp.status == 404, "Accepted invalid data"

    resp = await client.post(costs_per_hour_url, json={"metric_a": 3, "metric_b": 2})
    assert (
        resp.status == 200 and await resp.json() == 2 * 1 + 3 * 1.3
    ), "Rturned wrong result"


async def test_regular_run(
    app_with_first_write, perun_test_group, MeasurementClass, usage_delta, start_date
):
    """Tests the complete workflow of the application without any expected errors.

    Incoming data of the InfluxDB are simulated two times to trigger different
    scenarios (first measurement vs second measurement)"""
    app, http_client, influx_client, measurement1 = app_with_first_write
    assert (
        perun_test_group.credits_timestamps.value[MeasurementClass.metric.name]
        == start_date
    ), "Timestamp from measurement was not stored correctly in group"
    # let's send the second measurement
    measurement2 = replace(
        measurement1,
        timestamp=start_date + timedelta(days=7),
        value=measurement1.value + usage_delta,
    )
    billing_point = BillingHistory(
        measurement=perun_test_group.name,
        timestamp=measurement2.timestamp,
        credits_left=perun_test_group.credits_granted.value - usage_delta,
        metric_name=measurement2.metric.name,
        metric_friendly_name=measurement2.metric.friendly_name,
    )
    await write_and_mirror(app, http_client, influx_client, measurement2)
    await perun_test_group.connect()
    billing_points = await get_billing_history(perun_test_group, influx_client)
    assert perun_test_group.credits_timestamps.value[
        MeasurementClass.metric.name
    ] == start_date + timedelta(
        days=7
    ), "Timestamp from measurement was not stored correctly in group"
    # since our CREDITS_PER_VIRTUAL_HOUR are 1
    assert perun_test_group.credits_used.value == usage_delta
    assert [billing_point] == billing_points


async def test_50_percent_notification(
    app_with_first_write,
    perun_test_group,
    smtpserver,
    usage_delta,
    start_date,
    MeasurementClass,
):
    """Tests the complete workflow of the application without any expected errors but
    let the group fall under 50% of its granted credits.
    """
    app, http_client, influx_client, measurement1 = app_with_first_write
    # let's send the second measurement
    measurement2 = replace(
        measurement1,
        timestamp=start_date + timedelta(days=7),
        value=measurement1.value + usage_delta,
    )
    half_of_granted_credits = Decimal(perun_test_group.credits_granted.value / 2)
    perun_test_group.credits_used.value = half_of_granted_credits
    await perun_test_group.save()

    await write_and_mirror(app, http_client, influx_client, measurement2)
    await perun_test_group.connect()
    billing_point = BillingHistory(
        measurement=perun_test_group.name,
        timestamp=measurement2.timestamp,
        credits_left=half_of_granted_credits - usage_delta,
        metric_name=measurement2.metric.name,
        metric_friendly_name=measurement2.metric.friendly_name,
    )
    billing_points = await get_billing_history(perun_test_group, influx_client)
    assert perun_test_group.credits_timestamps.value[
        MeasurementClass.metric.name
    ] == start_date + timedelta(
        days=7
    ), "Timestamp from measurement was not stored correctly in group"
    # since our CREDITS_PER_VIRTUAL_HOUR are 1
    assert perun_test_group.credits_used.value == half_of_granted_credits + usage_delta
    assert [
        billing_point
    ] == billing_points, "Billing history has been stored incorrectly"
    assert len(smtpserver.outbox) == 1, "No notification has been send"


async def test_exception_during_send_notification(
    perun_test_group,
    aiohttp_client,
    os_credits_offline,
    influx_client,
    monkeypatch,
    MeasurementClass,
    start_date,
):
    """Makes sure that any error during sending of the notification does not crash the
    worker. Should also guarantee that no exception raised inside the original
    :func:`process_influx_line` can crash the worker.

    The sending fails because no smtpserver can be reached since the fixture is not
    requested.
    """
    from os_credits.notifications import EmailNotificationBase
    from os_credits.main import create_app
    import os_credits.credits.tasks

    # cannot use `app_with_first_write` since we have to monkeypatch first
    def fake_process_influx_line(*args, **kwargs):
        raise EmailNotificationBase(None, "test")

    measurement1 = MeasurementClass(
        measurement=MeasurementClass.metric.name,
        timestamp=start_date,
        location_id=perun_test_group.resource_id,
        project_name=perun_test_group.name,
        value=100,
    )

    monkeypatch.setattr(
        os_credits.credits.tasks, "process_influx_line", fake_process_influx_line
    )

    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)

    resp = await http_client.post("/write", data=measurement1.to_lineprotocol())
    assert resp.status == 202
    await app["task_queue"].join()
    # ugly code to access only worker task independent of its name
    # done() does also return true if the task exited with an exception
    assert not app["task_workers"][list(app["task_workers"].keys())[0]].done()


async def test_measurement_from_the_past(
    app_with_first_write, perun_test_group, usage_delta, start_date, MeasurementClass
):
    """Tests the correct behaviour in case of incoming measurements whose timestamps are
    not older than the stored one, which should never happen... But you never know"""

    app, http_client, influx_client, measurement1 = app_with_first_write
    # let's send the second measurement
    measurement2 = replace(measurement1, value=measurement1.value + usage_delta)

    await write_and_mirror(app, http_client, influx_client, measurement2)
    await influx_client.write(measurement2)
    resp = await http_client.post("/write", data=measurement2.to_lineprotocol())
    assert resp.status == 202
    # wait until request has been processed, indicated by the task finally calling
    # `task_done`
    await app["task_queue"].join()
    await perun_test_group.connect()
    billing_points = await get_billing_history(perun_test_group, influx_client)
    assert (
        perun_test_group.credits_timestamps.value[MeasurementClass.metric.name]
        == start_date
    ), "Timestamp of metric was updated although the measurement was invalid"
    assert perun_test_group.credits_used.value == 0
    assert [] == billing_points


async def test_equal_usage_values(
    app_with_first_write, perun_test_group, start_date, MeasurementClass
):
    """In contrast to :func:`test_regular_run` the second measurement does not have a
    higher usage value than the first one"""

    app, http_client, influx_client, measurement1 = app_with_first_write
    # let's send the second measurement
    measurement2 = replace(measurement1, timestamp=start_date + timedelta(days=7))

    await write_and_mirror(app, http_client, influx_client, measurement2)
    await perun_test_group.connect()
    assert (
        perun_test_group.credits_timestamps.value[MeasurementClass.metric.name]
        == start_date
    ), "Timestamp was updated although the measurement did not cause any billing"
    assert (
        perun_test_group.credits_used.value == 0
    ), "Group has been billed incorrectly, no changes expected"


async def test_no_billing_due_to_rounding(
    aiohttp_client, os_credits_offline, influx_client, perun_test_group, start_date
):
    """The measurements are all valid but no credits are billed and no timestamps
    updated when the second measurement is processed since the costs of the metric are
    so low they get lost when rounding according to given precision.
    
    Depending on the chosen rounding strategy multiple measurements have to processed
    before their accumulated usage delta leads to a billing."""
    from os_credits.main import create_app
    from os_credits.settings import config
    from os_credits.credits.base_models import (
        Metric,
        TotalUsageMetric,
        UsageMeasurement,
    )

    test_metric_name = "whole_run_test_cheap_1"

    class _TestMetricCheap(
        TotalUsageMetric, name=test_metric_name, friendly_name=test_metric_name
    ):
        # by setting the costs per hour this way we can be sure that the first billings
        # will be rounded to zero
        CREDITS_PER_VIRTUAL_HOUR = config["OS_CREDITS_PRECISION"] * Decimal("10") ** -1
        description = "Test Metric 1 for whole run test"

    @dataclass(frozen=True)
    class _TestMeasurementCheap(UsageMeasurement):
        metric: Type[Metric] = _TestMetricCheap

    measurement = _TestMeasurementCheap(
        measurement=test_metric_name,
        timestamp=start_date,
        location_id=perun_test_group.resource_id,
        project_name=perun_test_group.name,
        value=100,
    )
    usage_delta = 1

    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)

    await write_and_mirror(app, http_client, influx_client, measurement=measurement)
    # with default rounding Strategy ROUND_TO_HALF_EVEN
    # https://en.wikipedia.org/wiki/Rounding#Round_half_to_even
    # the following measurements will not cause any bills
    # choosing the ranges according to the amount of the credits to bill they accumulate
    for i in range(1, 6):
        measurement = replace(
            measurement,
            timestamp=measurement.timestamp + timedelta(days=7),
            value=measurement.value + usage_delta,
        )

        await write_and_mirror(app, http_client, influx_client, measurement)
        await perun_test_group.connect()
        billing_points = await get_billing_history(perun_test_group, influx_client)
        assert (
            perun_test_group.credits_timestamps.value[test_metric_name] == start_date
        ), "Timestamp from measurement was updated although no credits were billed"
        assert (
            perun_test_group.credits_used.value == 0
        ), """Credits were billed although this should not have happened given the required
        precision"""
        assert billing_points == []
    # this measurement should lead to a bill
    measurement = replace(
        measurement,
        timestamp=measurement.timestamp + timedelta(days=7),
        value=measurement.value + usage_delta,
    )
    await write_and_mirror(app, http_client, influx_client, measurement)
    await perun_test_group.connect()
    billing_points = await get_billing_history(perun_test_group, influx_client)
    expected_credits = config["OS_CREDITS_PRECISION"]
    billing_point = BillingHistory(
        measurement=perun_test_group.name,
        timestamp=measurement.timestamp,
        credits_left=(
            Decimal(perun_test_group.credits_granted.value)
            - config["OS_CREDITS_PRECISION"]
        ),
        metric_name=measurement.metric.name,
        metric_friendly_name=measurement.metric.friendly_name,
    )
    assert (
        perun_test_group.credits_timestamps.value[test_metric_name]
        == measurement.timestamp
    ), "Timestamp from measurement was updated although no credits were billed"
    assert (
        perun_test_group.credits_used.value == expected_credits
    ), """Credits were billed although this should not have happened given the required
    precision"""
    assert billing_points == [billing_point]


async def test_missing_previous_values(
    aiohttp_client,
    os_credits_offline,
    influx_client,
    perun_test_group,
    MeasurementClass,
    start_date,
    usage_delta,
):
    """Tests the complete workflow of the application without any expected errors.

    Incoming data of the InfluxDB are simulated two times to trigger different
    scenarios (first measurement vs second measurement)"""
    from os_credits.main import create_app

    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)
    measurement1 = MeasurementClass(
        measurement=MeasurementClass.metric.name,
        timestamp=start_date,
        location_id=perun_test_group.resource_id,
        project_name=perun_test_group.name,
        value=100,
    )

    # do not store the measurement in the InfluxDB (in contrast to `test_regular_run`)
    # since we want to test the behaviour where the entry corresponding to the timestamp
    # stored inside the group does not exist inside the InfluxDB (anymore)
    await write_and_mirror(
        app, http_client, influx_client=None, measurement=measurement1
    )
    # let's send the second measurement
    measurement2 = replace(
        measurement1,
        timestamp=start_date + timedelta(days=7),
        value=measurement1.value + usage_delta,
    )

    await write_and_mirror(app, http_client, influx_client, measurement2)
    await perun_test_group.connect()
    assert perun_test_group.credits_timestamps.value[
        MeasurementClass.metric.name
    ] == start_date + timedelta(
        days=7
    ), "Timestamp from measurement was not stored correctly in group"
    assert (
        perun_test_group.credits_used.value == 0
    ), """Group has been billed although the values of the previous measurement could
    not be retrieved"""
