from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from datetime import datetime
from typing import Any, Dict, List, Type, TypeVar, Union

from aioinflux.client import InfluxDBClient
from pandas import DataFrame

from .log import internal_logger
from .settings import config

INFLUX_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_DEFINITELY_PAST = datetime.fromtimestamp(0)

# TODO: Think about switching from DataFrame to JSON or other format, may InfluxDBPoint
# can be reused?
# would allow us to use alpine image and reduce dependencies


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


P = TypeVar("P", bound="InfluxDBPoint")


@dataclass
class InfluxDBPoint:
    # decoder functions should assume that their input values are strings
    measurement: str = field(metadata={"component": "measurement"})

    time: datetime = field(
        metadata={
            "component": "time",
            # influx stores times in nanoseconds, but last 6 digits are always zero
            # due to prometheus input data (which is using milliseconds)
            "decoder": lambda time_str: datetime.fromtimestamp(int(time_str) / 1e9),
            # does lose some preciseness unfortunately, but only nanoseconds
            "encoder": lambda ts: format(ts.timestamp() * 1e9, ".0f"),
        }
    )

    @classmethod
    def from_iterpoint(cls: Type[P], values: List[Any], meta: Dict[str, str]) -> P:
        """Only intended to be passed to the `iterpoints` method of `aioinflux` to parse
        the points and construct valid InfluxDBPoint instances.

        The metadata of dataclass attributes are used to parse and convert the necessary
        information, unknown values and tags are dropped.
        """
        measurement_name = meta["name"]
        combined_dict = dict(zip(meta["columns"], values))
        args: Dict[str, Any] = {
            "measurement": measurement_name,
            "time": datetime.fromtimestamp(combined_dict["time"] / 1e9),
        }
        for f in fields(cls):
            if not f.metadata or "component" not in f.metadata:
                # if the attribute has its own default value it's OK
                if f.default is not MISSING:
                    continue
                raise SyntaxError(
                    f"Attribute {f.name} has no metadata or component specified but at "
                    " least component must be specified to parse its value an Influx "
                    "Line."
                )
            if f.metadata["component"] in {"measurement", "time"}:
                continue
            elif f.metadata["component"] == "tag":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(
                    combined_dict[f.name]
                )
            # string field values are quoted, strip them
            elif f.metadata["component"] == "field":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(
                    combined_dict[f.name].strip('"')
                )
            elif f.metadata["component"] is None:
                internal_logger.debug(
                    "Skipping deserialization of attribute %s into InfluxDB Line "
                    "representation as requested",
                    f.name,
                )
                continue
            else:
                raise SyntaxError(
                    f"Unknown component for InfluxDB Line: {f.metadata['component']} "
                    f"for field {f.name}"
                )
        new_point = cls(**args)
        internal_logger.debug("Constructed %s", new_point)
        return new_point

    @classmethod
    def from_lineprotocol(cls: Type[P], influx_line_: Union[str, bytes]) -> P:
        """
        Creates a point from an InfluxDB Line, see
        https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/

        Deliberate usage of `cls` to allow and support potential subclassing.
        """
        if isinstance(influx_line_, bytes):
            influx_line = influx_line_.decode()
        else:
            influx_line = influx_line_
        internal_logger.debug("Converting InfluxDB Line `%s`")
        measurement_and_tag, field_set, time_str = influx_line.strip().split()
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
            if not f.metadata or "component" not in f.metadata:
                # if the attribute has its own default value it's OK
                if f.default is not MISSING:
                    continue
                raise SyntaxError(
                    f"Attribute {f.name} has no metadata or component specified but at "
                    " least component must be specified to parse its value an Influx "
                    "Line."
                )
            if f.metadata["component"] == "measurement":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(measurement_name)
            elif f.metadata["component"] == "time":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(time_str)
            elif f.metadata["component"] == "tag":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(tag_dict[f.name])
            # string field values are quoted, strip them
            elif f.metadata["component"] == "field":
                args[f.name] = f.metadata.get("decoder", lambda x: x)(
                    field_dict[f.name].strip('"')
                )
            elif f.metadata["component"] is None:
                internal_logger.debug(
                    "Skipping deserialization of attribute %s into InfluxDB Line "
                    "representation as requested",
                    f.name,
                )
                continue
            else:
                raise SyntaxError(
                    f"Unknown component for InfluxDB Line: {f.metadata['component']} "
                    f"for field {f.name}"
                )
        new_point = cls(**args)
        internal_logger.debug("Constructed %s", new_point)
        return new_point

    def to_lineprotocol(self) -> bytes:
        tag_dict: Dict[str, str] = {}
        field_dict: Dict[str, str] = {}
        measurement = ""
        time = ""
        for f in fields(self):
            # not raising an error since this would be raised every time for e.g.
            # `metric` of `UsageMeasurement`
            if not f.metadata:
                internal_logger.error(
                    "Could not insert attribute %s into InfluxDB Line representation, "
                    "missing metadata",
                    f.name,
                )
                continue
            if f.metadata["component"] == "measurement":
                measurement = f.metadata.get("encoder", str)(getattr(self, f.name))

            elif f.metadata["component"] == "time":
                time = f.metadata.get("encoder", str)(getattr(self, f.name))
            elif f.metadata["component"] == "tag":
                tag_dict[f.metadata.get("key", f.name)] = f.metadata.get(
                    "encoder", str
                )(getattr(self, f.name))
            elif f.metadata["component"] == "field":
                field_dict[f.metadata.get("key", f.name)] = f.metadata.get(
                    "encoder", lambda x: f'"{x}"'
                )(getattr(self, f.name))
            elif f.metadata["component"] is None:
                internal_logger.debug(
                    "Skipping serialization of attribute %s into InfluxDB Line "
                    "representation as requested",
                    f.name,
                )
                continue
        tag_str = ",".join(f"{key}={value}" for key, value in tag_dict.items())
        field_str = ",".join(f"{key}={value}" for key, value in field_dict.items())
        influx_line = " ".join([",".join([measurement, tag_str]), field_str, time])
        return influx_line.encode()
