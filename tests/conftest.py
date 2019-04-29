from asyncio import sleep
from importlib import reload
from logging import getLogger
from typing import Dict, List

from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError
from pytest import fixture
from pytest_docker_compose import NetworkInfo

from os_credits.influx.client import InfluxDBClient
from os_credits.settings import config

pytest_plugins = ["docker_compose"]

# how many credits does every group, created during test runs, have
TEST_INITIAL_CREDITS_GRANTED = 200


@fixture(name="one_worker_task", autouse=True)
def fixture_one_worker_task(monkeypatch):
    "Makes sure that only one worker task is used and that all settings are reset"
    from os_credits import settings

    monkeypatch.setenv("OS_CREDITS_WORKERS", "1")
    reload(settings)
    yield
    reload(settings)


@fixture(name="smtpserver")
def fixture_smtpserver(smtpserver, monkeypatch):
    monkeypatch.setenv("MAIL_SMTP_SERVER", str(smtpserver.addr[0]))
    monkeypatch.setenv("MAIL_SMTP_PORT", str(smtpserver.addr[1]))
    monkeypatch.setenv("MAIL_NOT_STARTTLS", "1")
    monkeypatch.setenv("CLOUD_GOVERNANCE_MAIL", "cloud@governance")
    return smtpserver


@fixture(name="influx_client")
async def fixture_influx_client(
    docker_network_info: Dict[str, List[NetworkInfo]], monkeypatch, loop
):

    influxdb_service = docker_network_info["test_influxdb"][0]
    monkeypatch.setenv("INFLUXDB_HOST", influxdb_service.hostname)
    monkeypatch.setenv("INFLUXDB_PORT", influxdb_service.host_port)
    monkeypatch.setenv("INFLUXDB_DB", "pytest")
    monkeypatch.setenv("INFLUXDB_USER", "")
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", "")
    influx_client = InfluxDBClient()
    influx_client.db = "pytest"
    getLogger("aioinflux").level = 0
    while True:
        # wait until InfluxDB is ready and up
        try:
            await influx_client.ping()
            break
        except (ClientOSError, ServerDisconnectedError):
            print("Sleeping for 1 second until InfluxDB is up")
            await sleep(1)
    # in production the application cannot create any databases since it does not admin
    # access to the InfluxDB and HTTP_AUTH is enabled, see the `project_usage` repo
    await influx_client.query(f"create database {config['CREDITS_HISTORY_DB']}")
    yield influx_client
    await influx_client.close()
