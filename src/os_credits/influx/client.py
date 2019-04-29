from __future__ import annotations

from datetime import datetime
from itertools import chain
from textwrap import shorten
from typing import AsyncGenerator, Dict, Iterable, List, Optional, Type, Union

from aioinflux import iterpoints
from aioinflux.client import InfluxDBClient as _InfluxDBClient

from os_credits.credits.base_models import UsageMeasurement
from os_credits.credits.models import BillingHistory
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

    async def ensure_history_db_exists(self) -> bool:
        """Checks whether the required database for credits history exists.

        :return: Whether the database exists
        """
        r = await self.show_databases()
        return config["CREDITS_HISTORY_DB"] in chain.from_iterable(
            r["results"][0]["series"][0]["values"]
        )

    async def query_points(
        self,
        measurement: str,
        point_class: Type[PT],
        db: str,
        query_constraints: Optional[List[str]] = None,
    ) -> AsyncGenerator[PT, None]:
        """Asynchronously yields all queried points which in turn are streamed in chunks
        from the InfluxDB, where the points are sorted by their timestamp descending.

        :param measurement: Which table to run the query against.
        :param point_class: Subclass of ``InfluxDBPoint`` whose ``from_iterpoint``
            method will be used to deserialize the returned points.
        :param db: Which database to run the query against.
        :param query_constraints: WHERE-constraints to add to the query, will be AND-ed
            if more than one is given.
        :return: Instances of ``point_class`` ordered by their timestamp descending.
        """
        query_template = """\
        SELECT *
        FROM {measurement}
        {constraints}
        ORDER BY time DESC
        """
        constraints = ""
        if query_constraints and len(query_constraints) > 0:
            constraints = f"WHERE {' AND '.join(query_constraints)}"
        query = query_template.format(constraints=constraints, measurement=measurement)
        influxdb_logger.debug(
            "Sending query `%s` to InfluxDB",
            shorten(query.replace("\n", ""), len(query)),
        )
        async for chunk in await self.query(query, chunked=True, db=db):
            for point in iterpoints(chunk, point_class.from_iterpoint):
                yield point

    async def query_points_since(
        self,
        measurement: str,
        point_class: Type[PT],
        db: str,
        since: datetime = _DEFINITELY_PAST,
        query_constraints: Optional[List[str]] = None,
    ) -> AsyncGenerator[PT, None]:
        """Wrapper around ``query_points`` to emulate ``WHERE time >= since`` constraint
        of InfluxDB.

        Necessary since it returns wrong results (for me), fixing definitely
        appreciated.

        :param since: Only return Points whose timestamp is >=, i.e. which are not older
        """
        async for point in self.query_points(
            measurement=measurement,
            point_class=point_class,
            db=db,
            query_constraints=query_constraints,
        ):
            if point.time >= since:
                yield point
            else:
                return

    async def previous_measurements(
        self, measurement: UsageMeasurement, since: datetime = _DEFINITELY_PAST
    ) -> Dict[datetime, UsageMeasurement]:
        """Return previous measurements for the same project and metric as the provided
        measurement.

        :param measurement: Must be initialized since its project and metric values are
            required.
        :param since: Passed through to ``query_points_since``.
        :return: Dictionary of measurements accessible by their timestamp which are
            sorted descending.
        """
        previous_measurements = self.query_points_since(
            measurement=measurement.metric.name,
            point_class=type(measurement),
            db=config["INFLUXDB_DB"],
            since=since,
            query_constraints=[f"project_name = '{measurement.project_name}'"],
        )
        return {point.time: point async for point in previous_measurements}

    async def write_billing_history(
        self, point: Union[BillingHistory, Iterable[BillingHistory]]
    ) -> None:
        await self.write(point, db=config["CREDITS_HISTORY_DB"])

    async def query_billing_history(
        self, project_name: str, since: datetime = _DEFINITELY_PAST
    ) -> AsyncGenerator[BillingHistory, None]:
        """Return the billing history of the specified project.

        :param project_name: Project whose history should be queried.
        :param since: Passed through to ``query_points_since``.
        :return: Asynchronously yielded instances of ``BillingHistory`` sorted by their
            timestamp descending.
        """
        return self.query_points_since(
            measurement=project_name,
            db=config["CREDITS_HISTORY_DB"],
            point_class=BillingHistory,
            since=since,
        )
