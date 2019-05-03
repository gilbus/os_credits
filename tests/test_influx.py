from dataclasses import dataclass, field
from datetime import datetime

from pytest import approx

from aioinflux import iterpoints
from os_credits.credits.models import BillingHistory
from os_credits.influx.client import InfluxDBClient
from os_credits.influx.model import InfluxDBPoint
from os_credits.settings import config


@dataclass(frozen=True)
class _TestPoint(InfluxDBPoint):
    field1: str
    tag1: str = field(metadata={"tag": True})


async def test_missing_db_exception(influx_client):
    influx_client.db = config["CREDITS_HISTORY_DB"]
    await influx_client.drop_database()
    assert (
        not await influx_client.ensure_history_db_exists()
    ), "Did not detect missing database"


async def test_history_exists(influx_client):

    now = datetime.now()

    credits_left = 300
    metric_name = metric_friendly_name = "test_history_metric"
    project_name = "test_history_measurement"
    point = BillingHistory(
        measurement=project_name,
        time=now,
        credits_left=credits_left,
        metric_name=metric_name,
        metric_friendly_name=metric_friendly_name,
    )
    await influx_client.write_billing_history(point)
    assert await influx_client.project_has_history(project_name)
    assert not await influx_client.project_has_history(f"not{project_name}")


def test_influx_line_conversion():

    influx_line = b'measurement,tag1=test field1="test" 1553342599293000000'

    point1 = _TestPoint.from_lineprotocol(influx_line)
    point2 = _TestPoint(
        measurement="measurement",
        field1="test",
        tag1="test",
        time=datetime(2019, 3, 23, 13, 3, 19, 293000),
    )
    assert point1 == point2, "Parsing from Line Protocol failed"
    # time has to be compared separately
    rest1, time1 = point1.to_lineprotocol().decode().rsplit(" ", 1)
    rest2, time2 = influx_line.decode().rsplit(" ", 1)
    # approx is necessary since we are losing some nanoseconds when converting
    assert rest1 == rest2 and int(time1) == approx(
        int(time2), 100
    ), "Construction of Line Protocol failed"


async def test_query_points(influx_client):
    point = _TestPoint(
        measurement="test_project_entries_query_measurement",
        tag1="test_project_entries_query",
        field1="test",
        time=datetime.now(),
    )
    await influx_client.write(point)
    previous_points = [
        point
        async for point in influx_client.query_points(
            point.measurement, type(point), db=influx_client.db
        )
    ]
    assert previous_points == [point]


async def test_influx_read_write(influx_client):
    point2 = _TestPoint(
        measurement="test_influx_read_write",
        tag1="test_influx_read_write",
        field1="test",
        time=datetime.now(),
    )
    await influx_client.write(point2)
    result = await influx_client.query("SELECT * FROM test_influx_read_write")
    parsed_point = list(iterpoints(result, _TestPoint.from_iterpoint))[0]
    assert parsed_point == point2


async def test_bool_serializer(influx_client):
    """Separate test since it is the only default serializer currently not in use
    """

    @dataclass(frozen=True)
    class BoolTest(InfluxDBPoint):
        t: bool
        f: bool = field(metadata={"tag": True})

    influx_line = b"bool_test,t=T f=FALSE 1553342599293000000"

    test1 = BoolTest.from_lineprotocol(influx_line)
    test2 = BoolTest(
        measurement="bool_test",
        time=datetime(2019, 3, 23, 13, 3, 19, 293000),
        f=False,
        t=True,
    )
    assert test1 == test2
    await influx_client.write(test2)
    result = await influx_client.query("SELECT * FROM bool_test")
    parsed_point = list(iterpoints(result, BoolTest.from_iterpoint))[0]
    assert parsed_point == test2


def test_sanitize_parameter():
    bad_param = "'\"\\;"
    sanitized_param = "\\'\\\"\\\\\\;"

    assert (
        InfluxDBClient.sanitize_parameter(bad_param) == sanitized_param
    ), "Sanitization of parameters for InfluxDB query failed"
