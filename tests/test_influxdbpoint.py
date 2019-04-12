from asyncio import sleep
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from pytest import approx, fixture

from aiohttp.client_exceptions import ClientOSError
from aioinflux import iterpoints
from os_credits.influxdb import InfluxClient, InfluxDBPoint
from pytest_docker_compose import NetworkInfo


@fixture(name="influx_client")
async def fixture_influx_client(
    docker_network_info: Dict[str, List[NetworkInfo]], monkeypatch, loop
):

    influxdb_service = docker_network_info["test_influxdb"][0]
    monkeypatch.setenv("INFLUXDB_HOST", influxdb_service.hostname)
    monkeypatch.setenv("INFLUXDB_DB", "pytest")
    monkeypatch.setenv("INFLUXDB_USER", "")
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", "")
    influx_client = InfluxClient()
    while True:
        # wait until InfluxDB is ready and up
        try:
            await influx_client.ping()
            break
        except ClientOSError:
            await sleep(1)
    return influx_client


@dataclass
class _TestPoint(InfluxDBPoint):
    tag1: int = field(metadata={"component": "tag", "decoder": int})
    field1: str = field(metadata={"component": "field"})


def test_influx_line_conversion():

    influx_line = b'measurement,tag1=3 field1="test" 1553342599293000000'

    point1 = _TestPoint.from_lineprotocol(influx_line)
    point2 = _TestPoint(
        measurement="measurement",
        tag1=3,
        field1="test",
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


async def test_influx_read_write(influx_client):
    point2 = _TestPoint(
        measurement="test_influx_read_write",
        tag1=3,
        field1="test",
        time=datetime(2019, 3, 23, 13, 3, 19, 293000),
    )
    await influx_client.write(point2)
    influx_client.output = "json"
    result = await influx_client.query("SELECT * FROM test_influx_read_write")
    parsed_point = list(iterpoints(result, _TestPoint.from_iterpoint))[0]
    assert parsed_point == point2