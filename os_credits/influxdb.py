from __future__ import annotations

from datetime import datetime

from aioinflux.client import InfluxDBClient
from pandas import DataFrame

from .settings import config
from .credits.measurements import Measurement

INFLUX_QUERY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class InfluxClient(InfluxDBClient):
    def __init__(self):
        super().__init__(**config["influxdb"], output="dataframe")

    async def entries_by_project_since(
        self, project_name: str, since: datetime, measurement: Measurement
    ) -> DataFrame:
        """
        Query the InfluxDB for any entries of the project identified by its name with a
        timestamp older or equal than `since`.
        :return: DataFrame containing the requested entries
        """
        query_teml = """\
        SELECT *
        FROM {measurement} 
        WHERE project_name = '{project_name}'
            AND time >= '{since}'
        """
        query = query_teml.format(
            project_name=project_name,
            since=since.strftime(INFLUX_QUERY_DATE_FORMAT),
            measurement=measurement.value,
        )
        return await self.query(query)
