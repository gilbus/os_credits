from __future__ import annotations

from datetime import datetime
from textwrap import shorten
from typing import AsyncGenerator, Dict, List, Optional, Type

from aioinflux import iterpoints
from aioinflux.client import InfluxDBClient as _InfluxDBClient
from os_credits.credits.base_models import UsageMeasurement
from os_credits.log import influxdb_logger
from os_credits.settings import config

from .model import PT

INFLUX_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"

_DEFINITELY_PAST = datetime.fromtimestamp(0)


class InfluxDBClient(_InfluxDBClient):
    def __init__(self) -> None:
        super().__init__(
            host=config["INFLUXDB_HOST"],
            port=config["INFLUXDB_PORT"],
            username=config["INFLUXDB_USER"],
            password=config["INFLUXDB_USER_PASSWORD"],
            database=config["INFLUXDB_DB"],
            output="json",
        )

    async def query_points(
        self,
        measurement: str,
        point_class: Type[PT],
        query_constraints: Optional[List[str]] = None,
    ) -> AsyncGenerator[PT, None]:
        """
        Yields all queried points which in turn are streamed in chunks from the
        InfluxDB, where the points are sorted by their timestamp descending
        """
        query_template = """\
        SELECT *
        FROM {measurement}
        {constraints}
        ORDER BY time DESC
        """
        constraints = ""
        if query_constraints and len(query_constraints) > 0:
            constraints = f"WHERE {'AND'.join(query_constraints)}"
        query = query_template.format(constraints=constraints, measurement=measurement)
        influxdb_logger.debug(
            "Sending query `%s` to InfluxDB",
            shorten(query.replace("\n", ""), len(query)),
        )

        async for chunk in await self.query(query, chunked=True):
            for point in iterpoints(chunk, point_class.from_iterpoint):
                yield point

    async def previous_measurements(
        self, measurement: "UsageMeasurement", since: datetime = _DEFINITELY_PAST
    ) -> Dict[datetime, "UsageMeasurement"]:
        previous_measurements: Dict[datetime, "UsageMeasurement"] = {}
        async for point in self.query_points(
            measurement=measurement.metric.measurement_name,
            point_class=type(measurement),
            query_constraints=[f"project_name = '{measurement.project_name}'"],
        ):
            if point.time >= since:
                previous_measurements[point.time] = point
            else:
                break

        return previous_measurements
