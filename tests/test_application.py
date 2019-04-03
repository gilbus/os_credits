from datetime import datetime, timedelta
from importlib import reload

from pytest import fixture, mark

from os_credits import settings


@fixture(autouse=True)
def reload_conf_module():
    reload(settings)


@fixture(name="credits_env")
def fixture_credits_env(monkeypatch):
    monkeypatch.setenv("OS_CREDITS_PERUN_VO_ID", "0")
    monkeypatch.setenv("OS_CREDITS_PERUN_LOGIN", "0")
    monkeypatch.setenv("OS_CREDITS_PERUN_PASSWORD", "0")
    monkeypatch.setenv("OS_CREDITS_DUMMY_MODE", "1")
    monkeypatch.setenv("INFLUXDB_HOST", "0")
    monkeypatch.setenv("INFLUXDB_USER", "0")
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", "0")
    monkeypatch.setenv("INFLUXDB_DB", "0")


async def test_settings(monkeypatch):
    monkeypatch.setenv("OS_CREDITS_PROJECT_WHITELIST", "ProjectA;ProjectB")
    monkeypatch.setenv("OS_CREDITS_PRECISION", "98")
    # necessary to pickup different environment variables
    reload(settings)
    from os_credits.settings import config

    assert config["OS_CREDITS_PROJECT_WHITELIST"] == {
        "ProjectA",
        "ProjectB",
    }, "Comma-separated list was not parsed correctly from environment"
    assert (
        config["OS_CREDITS_PRECISION"] == 98
    ), "Integer value was not parsed/converted correctly from environment"


async def test_startup(aiohttp_client, credits_env):
    from os_credits.main import create_app

    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/ping")
    text = await resp.text()
    assert resp.status == 200 and text == "Pong", "/ping endpoint failed"
    # check for correct parsing and processing of settings via env vars


async def test_credits_endpoint(aiohttp_client, credits_env):
    from os_credits.main import create_app
    from os_credits.credits.measurements import Metric

    app = await create_app()
    client = await aiohttp_client(app)

    class _MeasurementA(
        Metric, measurement_name="measurement_a", friendly_name="measurement_a"
    ):
        CREDITS_PER_VIRTUAL_HOUR = 1.3
        property_description = "Test measurement A"

        @classmethod
        def api_information(cls):
            return {
                "type": "str",
                "description": cls.property_description,
                "measurement_name": cls.measurement_name,
            }

    class Measurement1(Metric, measurement_name="test2", friendly_name="test2"):
        CREDITS_PER_VIRTUAL_HOUR = 1

    resp = await client.get("/credits")
    measurements = await resp.json()
    assert resp.status == 200 and measurements["measurement_a"] == {
        "description": "Test measurement A",
        "type": "str",
        "measurement_name": "measurement_a",
    }, "GET /credits returned wrong body"

    resp = await client.post("/credits", json={"DefinitelyNotExisting": "test"})
    assert resp.status == 404, "POST /credits accepted invalid data"

    resp = await client.post("/credits", json={"test2": 2, "measurement_a": 3})
    json = await resp.json()
    assert (
        resp.status == 200 and json == 2 * 1 + 3 * 1.3
    ), "POST /credits returned wrong result"


# actual influx line `project_mb_usage,__name__=project_mb_usage,domain_id=e049ffa7b625b12f,domain_name=elixir,instance=usage_exporter:8080,job=project_usages,lo
# cation=site-a,location_id=8487,project_id=815070460d3a32ef,project_name=credits_2 value=555.3362602666667 1553342599293000000`
async def test_initial_measurements(aiohttp_client, credits_env, monkeypatch):
    from os_credits.main import create_app
    from os_credits.credits.measurements import Metric
    from os_credits.perun.groupsManager import Group

    start_date = datetime.now()

    test_initial_credits = 200
    test_measurent_name = "whole_run_test_1"
    test_group_name = "test_run_1"
    test_location_id = 1111
    test_group = Group(test_group_name, test_location_id)

    monkeypatch.setenv("OS_CREDITS_DUMMY_CREDITS_GRANTED", f"{test_initial_credits}")
    reload(settings)

    class _TestMeasurement1(
        Metric, measurement_name=test_measurent_name, friendly_name=test_measurent_name
    ):
        CREDITS_PER_VIRTUAL_HOUR = 1
        property_description = "Test Metric 1 for whole run test"

    influx_line_template = (
        "{measurement_name},location_id={location_id},"
        "project_name={group_name} value={value} {timestamp_ns:.0f}"
    )

    initial_line = influx_line_template.format(
        value=100,
        timestamp_ns=start_date.timestamp() * 1e9,
        group_name=test_group_name,
        location_id=test_location_id,
        measurement_name=test_measurent_name,
    )
    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.post("/write", data=initial_line)
    assert resp.status == 202
    # wait until request has been processed, indicated by the task finally calling
    # `task_done`
    await app["task_queue"].join()
    await test_group.connect()
    assert (
        test_group.credits_granted.value
        == test_group.credits_current.value
        == test_initial_credits
    ), "Initial copy from credits_granted to credits_current failed"
    assert (
        test_group.credits_timestamps.value[test_measurent_name] == start_date
    ), "Timestamp from measurement was not stored correctly in group"


@mark.skip("Not yet, requires working InfluxDB")
async def test_whole_run(aiohttp_client, credits_env, monkeypatch):
    from os_credits.main import create_app
    from os_credits.credits.measurements import Metric
    from os_credits.perun.groupsManager import Group

    start_date = datetime.now()

    test_initial_credits = 200
    test_measurent_name = "whole_run_test_1"
    test_group_name = "test_run_1"
    test_location_id = 1111
    test_group = Group(test_group_name, test_location_id)

    monkeypatch.setenv("OS_CREDITS_DUMMY_CREDITS_GRANTED", f"{test_initial_credits}")
    reload(settings)

    class _TestMeasurement1(
        Metric, measurement_name=test_measurent_name, friendly_name=test_measurent_name
    ):
        CREDITS_PER_VIRTUAL_HOUR = 1
        property_description = "Test Metric 1 for whole run test"

    influx_line_template = (
        "{measurement_name},location_id={location_id},"
        "project_name={group_name} value={value} {timestamp_ns:.0f}"
    )

    initial_line = influx_line_template.format(
        value=100,
        timestamp_ns=start_date.timestamp() * 1e9,
        group_name=test_group_name,
        location_id=test_location_id,
        measurement_name=test_measurent_name,
    )
    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.post("/write", data=initial_line)
    assert resp.status == 202
    # wait until request has been processed, indicated by the task finally calling
    # `task_done`
    await app["task_queue"].join()
    await test_group.connect()
    assert (
        test_group.credits_granted.value
        == test_group.credits_current.value
        == test_initial_credits
    ), "Initial copy from credits_granted to credits_current failed"
    assert (
        test_group.credits_timestamps.value[test_measurent_name] == start_date
    ), "Timestamp from measurement was not stored correctly in group"
    next_line = influx_line_template.format(
        value=103,
        # timestamp should not matter since this measurement uses the base
        # implementation where virtual {cpu,ram}-hours are billed
        timestamp_ns=(start_date + timedelta(days=7)).timestamp() * 1e9,
        group_name=test_group_name,
        location_id=test_location_id,
        measurement_name=test_measurent_name,
    )
    resp = await client.post("/write", data=next_line)
    assert resp.status == 202
    # wait until request has been processed, indicated by the task finally calling
    # `task_done`
    await app["task_queue"].join()
    await test_group.connect()
    assert (
        test_group.credits_granted.value == test_initial_credits
    ), "Initial copy from credits_granted to credits_current failed"
    assert test_group.credits_current.value == 197
    assert (
        test_group.credits_timestamps.value[test_measurent_name] == start_date
    ), "Timestamp from measurement was not stored correctly in group"
