from dataclasses import dataclass, field
from datetime import datetime

from pytest import approx

from aioinflux import iterpoints
from os_credits.influx.model import InfluxDBPoint
from os_credits.settings import config


@dataclass(frozen=True)
class _TestPoint(InfluxDBPoint):
    field1: str = field(metadata={"component": "field"})
    tag1: str = field(metadata={"component": "tag"})


async def test_missing_db_exception(influx_client):
    influx_client.db = config["CREDITS_HISTORY_DB"]
    await influx_client.drop_database()
    assert (
        not await influx_client.ensure_history_db_exists()
    ), "Did not detect missing database"


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
        async for point in influx_client.query_points(point.measurement, type(point))
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
