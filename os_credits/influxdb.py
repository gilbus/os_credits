from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, Mapping

from aioinflux import lineprotocol
from aioinflux.client import InfluxDBClient
from aioinflux.serialization.usertype import FLOAT, MEASUREMENT, STR, TAG, TIMEDT
from pandas import DataFrame

from .log import internal_logger
from .settings import config

INFLUX_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_DEFINITELY_PAST = datetime.fromtimestamp(0)


class InfluxClient(InfluxDBClient):
    def __init__(self) -> None:
        super().__init__(
            host=config["INFLUXDB_HOST"],
            port=config["INFLUXDB_PORT"],
            username=config["INFLUXDB_USER"],
            password=config["INFLUXDB_USER_PASSWORD"],
            database=config["INFLUXDB_DB"],
            output="dataframe",
        )

    async def entries_by_project_since(
        self,
        project_name: str,
        measurement_name: str,
        since: datetime = _DEFINITELY_PAST,
    ) -> DataFrame:
        """
        Query the InfluxDB for any entries of the project identified by its name with a
        timestamp older or equal than `since`.
        :return: DataFrame containing the requested entries
        """
        query_template = """\
        SELECT *
        FROM {measurement}
        WHERE project_name = '{project_name}'
            AND time >= '{since}'
        """
        query = query_template.format(
            project_name=project_name,
            since=since.strftime(INFLUX_QUERY_DATE_FORMAT),
            measurement=measurement_name,
        )
        return await self.query(query)


@lineprotocol(
    schema={
        "measurement_name": MEASUREMENT,
        "timestamp": TIMEDT,
        "location_id": TAG,
        "project_name": TAG,
        "value": FLOAT,
    }
)
@dataclass(frozen=True)
class InfluxDBPoint:
    # this two properties are always present
    measurement_name: str = field(metadata={"component": "measurement"})

    # influx stores timestamps in nanoseconds, but last 6 digits are always zero due to
    # prometheus input data (which is using milliseconds)
    # convert to unix timestamp by division without losing any information since those
    # are stored in the `microseconds` attribute of the datetime object
    timestamp: datetime = field(
        metadata={
            "component": "timestamp",
            "converter": lambda ts: datetime.fromtimestamp(int(ts) / 1e9),
        }
    )
    # properties will be extracted from influx line protocol as specified
    # if your chosen name for any attribute differs from the key inside the InfluxDB
    # Line specify the key via `name` inside the metadata
    location_id: int = field(metadata={"component": "tag", "converter": int})
    project_name: str = field(metadata={"component": "tag"})
    value: float = field(metadata={"component": "field", "converter": float})

    @classmethod
    def from_influx_line(cls, influx_line: str) -> InfluxDBPoint:
        """
        Creates a point from an InfluxDB Line, see
        https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/

        Deliberate usage of `cls` to allow and support potential subclassing.
        """
        internal_logger.debug("Converting InfluxDB Line `%s`")
        measurement_and_tag, field_set, timestamp_str = influx_line.strip().split()
        measurement_name, tag_set = measurement_and_tag.split(",", 1)
        tag_dict: Dict[str, str] = {}
        field_dict: Dict[str, str] = {}
        for tag_pair in tag_set.split(","):
            tag_name, tag_value = tag_pair.split("=", 1)
            tag_dict.update({tag_name: tag_value})
        for field_pair in field_set.split(","):
            field_name, field_value = field_pair.split("=", 1)
            field_dict.update({field_name: field_value})
        args: Dict[str, Any] = {}
        for f in fields(cls):
            if not f.metadata or not f.metadata["component"]:
                raise SyntaxError(
                    f"Attribute {f.name} has no metadata or component specified but at "
                    " least component must be specified."
                )
            if f.metadata["component"] == "measurement":
                args[f.name] = f.metadata.get("converter", lambda x: x)(
                    measurement_name
                )
            elif f.metadata["component"] == "timestamp":
                args[f.name] = f.metadata.get("converter", lambda x: x)(timestamp_str)
            elif f.metadata["component"] == "tag":
                args[f.name] = f.metadata.get("converter", lambda x: x)(
                    tag_dict[f.metadata.get("key", f.name)]
                )
            elif f.metadata["component"] == "field":
                args[f.name] = f.metadata.get("converter", lambda x: x)(
                    field_dict[f.metadata.get("key", f.name)]
                )
            else:
                raise SyntaxError(
                    f"Unknown component for InfluxDB Line: {f.metadata['component']} "
                    f"for field {f.name}"
                )
        new_point = cls(**args)
        internal_logger.debug("Constructed %s", new_point)
        return new_point
