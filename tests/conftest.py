from asyncio import sleep
from importlib import reload
from logging import getLogger

from aiohttp.client_exceptions import ClientOSError, ServerDisconnectedError
from pytest import fixture

from os_credits.influx.client import InfluxDBClient
from os_credits.perun.group import Group
from os_credits.settings import config

# how many credits does every group, created during test runs, have
TEST_INITIAL_CREDITS_GRANTED = 200


@fixture(name="perun_test_group")
def fixture_perun_test_group() -> Group:
    # these are real objects inside Perun so do not change them, otherwise all perun
    # tests will fail
    group_id = 11482
    group_name = "os_credits_test"
    resource_id = 8676
    # resource_name = "test"

    group = Group(group_name, resource_id)
    # set the group_id already
    group.id = group_id
    return group


@fixture(name="settings_reload_after_use", autouse=True)
def fixture_settings_reload_after_use():
    "Make sure that settings are reset after every run"
    from os_credits import settings

    yield
    reload(settings)


@fixture(name="smtpserver")
def fixture_smtpserver(smtpserver, monkeypatch):
    from os_credits import settings

    monkeypatch.setenv("MAIL_SMTP_SERVER", str(smtpserver.addr[0]))
    monkeypatch.setenv("MAIL_SMTP_PORT", str(smtpserver.addr[1]))
    monkeypatch.setenv("MAIL_NOT_STARTTLS", "1")
    reload(settings)
    return smtpserver


@fixture(name="influx_client")
async def fixture_influx_client(loop):

    influx_client = InfluxDBClient(loop=loop)
    influx_client.db = config["INFLUXDB_DB"]
    getLogger("aioinflux").level = 0
    await influx_client.ping()
    # in production the application cannot create any databases since it does not admin
    # access to the InfluxDB and HTTP_AUTH is enabled, see the `project_usage` repo
    await influx_client.query(f"create database {config['CREDITS_HISTORY_DB']}")
    while True:
        try:
            await influx_client.ping()
            break
        except (ClientOSError, ServerDisconnectedError):
            print("Sleeping for 1 second until InfluxDB is up")
            await sleep(1)
    yield influx_client
    # clear all data from pytest and credits_history_db
    await influx_client.query("drop series from /.*/", db="pytest")
    # fails sometimes, ignore
    try:
        await influx_client.query(
            "drop series from /.*/", db=config["CREDITS_HISTORY_DB"]
        )
    except Exception:
        pass
    await influx_client.close()
