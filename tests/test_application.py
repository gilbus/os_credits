async def test_startup(aiohttp_client, monkeypatch):
    # must be available in the environment so the app is able to launch completely
    monkeypatch.setenv("OS_CREDITS_PERUN_VO_ID", 0)
    monkeypatch.setenv("OS_CREDITS_PERUN_LOGIN", 0)
    monkeypatch.setenv("OS_CREDITS_PERUN_PASSWORD", 0)
    monkeypatch.setenv("OS_CREDITS_PROJECT_WHITELIST", "ProjectA;ProjectB")
    monkeypatch.setenv("OS_CREDITS_PRECISION", "98")
    monkeypatch.setenv("INFLUXDB_HOST", 0)
    monkeypatch.setenv("INFLUXDB_USER", 0)
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", 0)
    monkeypatch.setenv("INFLUXDB_DB", 0)

    from os_credits.main import create_app
    from os_credits.settings import config

    app = await create_app()
    client = await aiohttp_client(app)
    resp = await client.get("/ping")
    text = await resp.text()
    assert resp.status == 200 and text == "Pong", "/ping endpoint failed"
    # check for correct parsing and processing of settings via env vars
    assert config["OS_CREDITS_PROJECT_WHITELIST"] == {"ProjectA", "ProjectB"}
    assert config["OS_CREDITS_PRECISION"] == 98
