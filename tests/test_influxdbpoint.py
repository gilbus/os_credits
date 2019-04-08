from dataclasses import dataclass, field
from datetime import datetime

from pytest import approx

from os_credits.influxdb import InfluxDBPoint


@dataclass
class _TestPoint(InfluxDBPoint):
    attr1: int = field(metadata={"component": "tag", "decoder": int, "key": "tag1"})
    value1: float = field(metadata={"component": "field"})


def test_influx_line_conversion():

    influx_line = b"measurement,tag1=3 value1=vkey1 1553342599293000000"

    point1 = _TestPoint.from_influx_line(influx_line)
    point2 = _TestPoint(
        measurement="measurement",
        attr1=3,
        value1="vkey1",
        timestamp=datetime(2019, 3, 23, 13, 3, 19, 293000),
    )
    assert point1 == point2, "Parsing from Line Protocol failed"
    # timestamp has to be compared separately
    rest1, timestamp1 = point1.to_lineprotocol().decode().rsplit(" ", 1)
    rest2, timestamp2 = influx_line.decode().rsplit(" ", 1)
    # approx is necessary since we are losing some nanoseconds when converting
    assert rest1 == rest2 and int(timestamp1) == approx(
        int(timestamp2), 100
    ), "Construction of Line Protocol failed"
