from __future__ import annotations

from dataclasses import MISSING, dataclass, fields
from datetime import datetime
from typing import Any, AnyStr, Dict, List, Type, TypeVar

from os_credits.log import internal_logger

from .helper import deserialize, serialize

INFLUX_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_DEFINITELY_PAST = datetime.fromtimestamp(0)

# PointType
PT = TypeVar("PT", bound="InfluxDBPoint")


@dataclass(frozen=True)
class InfluxDBPoint:
    """Base class of all data models whose content is written or read from the InfluxDB.

    To define a data model as shown in the official InfluxDB Line Tutorial extend in the
    following way

    >>> from dataclasses import dataclass, field
    >>> from os_credits.influx.model import InfluxDBPoint
    >>> @dataclass(frozen=True)
    ... class Weather(InfluxDBPoint):
    ...     location: str = field(metadata={'tag': True})
    ...     temperature: int
    >>> from datetime import datetime
    >>> timestamp = datetime(2016, 6, 13, 19, 43, 50, 100400)
    >>> weather = Weather('weather', timestamp, 'us-midwest', 82)
    >>> print(weather.to_lineprotocol())
    b'weather,location=us-midwest temperature=82 1465839830100399872'
    >>> Weather.from_lineprotocol(weather.to_lineprotocol()) == weather
    True

    Unfortunately *InfluxDB* does store all timestamps as nanoseconds which are not
    natively supported by python. We are therefore losing some precision but this is
    negligible since the timestamps of *Prometheus* are only milliseconds.
    """

    measurement: str
    """The name of this measurement"""
    timestamp: datetime

    @classmethod
    def from_iterpoint(cls: Type[PT], values: List[Any], meta: Dict[str, str]) -> PT:
        """Only intended to be passed to the ``iterpoints`` method of ``aioinflux`` to
        parse the points and construct valid InfluxDBPoint instances.

        The metadata of dataclass attributes are used to parse and convert the necessary
        information, unknown values and tags are dropped.
        """
        measurement_name = meta["name"]
        combined_dict = dict(zip(meta["columns"], values))
        args: Dict[str, Any] = {
            "measurement": measurement_name,
            "timestamp": deserialize(combined_dict["time"], datetime),
        }
        for f in fields(cls):
            if f.default is not MISSING:
                continue
            # values of this fields are already known
            if f.name in args:
                continue
            args[f.name] = deserialize(combined_dict[f.name], f)
        new_point = cls(**args)
        internal_logger.debug("Constructed %s", new_point)
        return new_point

    @classmethod
    def from_lineprotocol(cls: Type[PT], influx_line_: AnyStr) -> PT:
        """
        Creates a point from an InfluxDB Line, see
        https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/

        Deliberate usage of `cls` to allow and support potential subclassing.
        """
        if isinstance(influx_line_, bytes):
            influx_line = influx_line_.decode()
        else:
            influx_line = influx_line_
        internal_logger.debug("Converting InfluxDB Line `%s`", influx_line)
        measurement_and_tag, field_set, timestamp_str = influx_line.strip().split()
        measurement_name, tag_set = measurement_and_tag.split(",", 1)
        tag_field_dict: Dict[str, str] = {}
        for tag_pair in tag_set.split(","):
            tag_name, tag_value = tag_pair.split("=", 1)
            tag_field_dict.update({tag_name: tag_value})
        for field_pair in field_set.split(","):
            field_name, field_value = field_pair.split("=", 1)
            tag_field_dict.update({field_name: field_value})
        args: Dict[str, Any] = {
            "measurement": measurement_name,
            "timestamp": deserialize(timestamp_str, datetime),
        }
        for f in fields(cls):
            if f.default is not MISSING:
                continue
            # values of this fields are already known
            if f.name in args:
                continue
            is_tag = False
            if f.metadata and f.metadata.get("tag", False):
                is_tag = True
            if f.name not in tag_field_dict:
                raise KeyError(
                    f"InfluxDB Line does not contain {'tag' if is_tag else 'field'} "
                    "`{f.name}`"
                )
            value = tag_field_dict[f.name]
            # string field values are quoted, strip them
            if not is_tag and isinstance(value, str):
                value = value.strip('"')
            args[f.name] = deserialize(value, f)
        new_point = cls(**args)
        internal_logger.debug("Constructed %s", new_point)
        return new_point

    def to_lineprotocol(self) -> bytes:
        tag_dict: Dict[str, str] = {}
        field_dict: Dict[str, str] = {}
        measurement = self.measurement
        timestamp = format(serialize(self.timestamp), ".0f")
        for f in fields(self):
            if f.name in {"measurement", "timestamp"}:
                continue
            # For now skip all fields and tags which have a default value
            # TODO: evaluate
            if f.default is not MISSING:
                continue
            value = getattr(self, f.name)
            if f.metadata and f.metadata.get("tag", False):
                tag_dict[f.name] = str(serialize(value, f))
            else:
                component_value = serialize(value, f)
                # string field values must be quoted
                if isinstance(component_value, str):
                    field_dict[f.name] = str(serialize(f'"{component_value}"', f))
                else:
                    field_dict[f.name] = str(serialize(component_value, f))
        tag_str = ",".join(f"{key}={value}" for key, value in tag_dict.items())
        field_str = ",".join(f"{key}={value}" for key, value in field_dict.items())
        influx_line = " ".join(
            [",".join([measurement, tag_str]), field_str, str(timestamp)]
        )
        return influx_line.encode()
