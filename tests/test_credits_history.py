from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

from os_credits.credits.base_models import Credits
from os_credits.credits.models import BillingHistory
from os_credits.influx.client import InfluxDBClient
from os_credits.main import create_app

datetime_format = "%Y-%m-%d %H:%M:%S"


async def test_api_endpoint(influx_client: InfluxDBClient, aiohttp_client):
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    tomorrow = now + timedelta(days=1)

    credits_left = Credits(Decimal(300))
    metric_name = metric_friendly_name = "test_history_metric"
    project_name = "test_history_measurement"
    point = BillingHistory(
        measurement=project_name,
        timestamp=now,
        credits_left=credits_left,
        metric_name=metric_name,
        metric_friendly_name=metric_friendly_name,
    )
    await influx_client.write_billing_history(point)
    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)
    resp1 = await http_client.get(
        app.router["api_credits_history"].url_for(project_name=project_name)
    )
    resp2 = await http_client.get(
        app.router["api_credits_history"]
        .url_for(project_name=project_name)
        .with_query(
            {
                "start_date": yesterday.strftime(datetime_format),
                "end_date": tomorrow.strftime(datetime_format),
            }
        )
    )
    expected_resp = dict(
        credits=["credits", point.credits_left],
        metrics=["metrics", point.metric_friendly_name],
        timestamps=["timestamps", point.timestamp.strftime(datetime_format)],
    )
    assert resp1.status == resp2.status == HTTPStatus.OK
    assert await resp1.json() == await resp2.json() == expected_resp
    resp1 = await http_client.get(
        app.router["api_credits_history"]
        .url_for(project_name=project_name)
        .with_query({"start_date": tomorrow.strftime(datetime_format)})
    )
    resp2 = await http_client.get(
        app.router["api_credits_history"]
        .url_for(project_name=project_name)
        .with_query({"end_date": yesterday.strftime(datetime_format)})
    )
    assert resp1.status == resp2.status == HTTPStatus.NO_CONTENT


async def test_invalid_params(aiohttp_client, influx_client):
    app = await create_app(_existing_influxdb_client=influx_client)
    http_client = await aiohttp_client(app)

    resp = await http_client.get(
        # a totally empty project_name would result in a 404
        app.router["api_credits_history"].url_for(project_name="  ")
    )

    assert resp.status == HTTPStatus.BAD_REQUEST, "Empty project_name accepted"
    resp = await http_client.get(
        app.router["api_credits_history"]
        .url_for(project_name="unknown")
        .with_query(
            {"start_date": "2019-01-01 00:00:01", "end_date": "2019-01-01 00:00:00"}
        )
    )
    assert (
        resp.status == HTTPStatus.BAD_REQUEST
    ), "Accepted invalid combination of date params"
