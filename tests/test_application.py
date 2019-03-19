from pytest import fixture


@fixture(name="credits_env")
def fixture_credits_env(monkeypatch):
    monkeypatch.setenv("OS_CREDITS_PERUN_VO_ID", "0")
    monkeypatch.setenv("OS_CREDITS_PERUN_LOGIN", "0")
    monkeypatch.setenv("OS_CREDITS_PERUN_PASSWORD", "0")
    monkeypatch.setenv("INFLUXDB_HOST", "0")
    monkeypatch.setenv("INFLUXDB_USER", "0")
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", "0")
    monkeypatch.setenv("INFLUXDB_DB", "0")


async def test_settings(monkeypatch):
    monkeypatch.setenv("OS_CREDITS_PROJECT_WHITELIST", "ProjectA;ProjectB")
    monkeypatch.setenv("OS_CREDITS_PRECISION", "98")
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
    from os_credits.credits.measurements import Measurement

    app = await create_app()
    client = await aiohttp_client(app)

    class _MeasurementA(
        Measurement, prometheus_name="measurement_a", friendly_name="measurement_a"
    ):
        CREDITS_PER_HOUR = 1.3
        property_description = "Test measurement A"

        @classmethod
        def api_information(cls):
            return {
                "type": "str",
                "description": cls.property_description,
                "prometheus_name": cls.prometheus_name,
            }

    class Measurement1(Measurement, prometheus_name="test2", friendly_name="test2"):
        CREDITS_PER_HOUR = 1

    resp = await client.get("/credits")
    measurements = await resp.json()
    assert resp.status == 200 and measurements["measurement_a"] == {
        "description": "Test measurement A",
        "type": "str",
        "prometheus_name": "measurement_a",
    }, "GET /credits returned wrong body"

    resp = await client.post("/credits", json={"DefinitelyNotExisting": "test"})
    assert resp.status == 404, "POST /credits accepted invalid data"

    resp = await client.post("/credits", json={"test2": 2, "measurement_a": 3})
    json = await resp.json()
    assert (
        resp.status == 200 and json == 2 * 1 + 3 * 1.3
    ), "POST /credits returned wrong result"
