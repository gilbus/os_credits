from asyncio import wait_for
from datetime import datetime

from os_credits.credits.models import BillingHistory
from os_credits.influx.client import InfluxDBClient
from os_credits.main import create_app


async def test_api_endpoint(influx_client: InfluxDBClient, aiohttp_client):
    now = datetime.now()
    credits_left = 300
    metric_name = metric_friendly_name = "test_history_metric"
    project_name = "test_history_measurement"
    point = BillingHistory(
        measurement=project_name,
        time=now,
        credits_left=credits_left,
        metric_name=metric_name,
        metric_friendly_name=metric_friendly_name,
    )
    await wait_for(influx_client.write_billing_history(point), timeout=None)
    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.get(f"/api/credits_history/{project_name}")
    expected_resp = dict(
        credits=["credits", point.credits_left],
        metrics=["metrics", point.metric_friendly_name],
        timestamps=["timestamps", point.time.strftime("%Y-%m-%d %H:%M:%S")],
    )
    assert 200 == resp.status
    assert expected_resp == await resp.json()
