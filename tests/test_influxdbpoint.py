from dataclasses import dataclass, field
from datetime import datetime

from os_credits.influxdb import InfluxDBPoint


@dataclass
class _TestPoint(InfluxDBPoint):
    attr1: int = field(metadata={"component": "tag", "decoder": int, "key": "tag1"})
    value1: float = field(metadata={"component": "field"})


def test_influx_line_conversion():

    influx_line = "measurement,tag1=3,a=b value1=vkey1,b=c 1553342599293000000"

    point1 = _TestPoint.from_influx_line(influx_line)
    point2 = _TestPoint(
        measurement="measurement",
        attr1=3,
        value1="vkey1",
        timestamp=datetime(2019, 3, 23, 13, 3, 19, 293000),
    )
    assert point1 == point2
