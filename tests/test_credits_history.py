from asyncio import wait_for
from datetime import datetime

from os_credits.credits.models import BillingHistory
from os_credits.influx.client import InfluxDBClient
from os_credits.main import create_app


async def test_api_endpoint(influx_client: InfluxDBClient, aiohttp_client):
    now = datetime.now()
    credits = 300
    metric_name = metric_friendly_name = "test_history_metric"
    project_name = "test_history_measurement"
    point = BillingHistory(
        measurement=project_name,
        time=now,
        credits=credits,
        metric_name=metric_name,
        metric_friendly_name=metric_friendly_name,
    )
    await wait_for(influx_client.write_billing_history(point), timeout=None)
    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.get(f"/credits_history/{project_name}")
    assert 200 == resp.status
    assert {
        point.time.isoformat(): dict(credits=point.credits, metric=point.metric_name)
    } == await resp.json()
