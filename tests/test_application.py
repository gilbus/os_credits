async def test_startup(test_client, monkeypatch):
    # must be available in the environment so the app is able to launch completely
    monkeypatch.setenv("OS_CREDITS_PERUN_VO_ID", 0)
    monkeypatch.setenv("OS_CREDITS_PERUN_LOGIN", 0)
    monkeypatch.setenv("OS_CREDITS_PERUN_PASSWORD", 0)
    monkeypatch.setenv("INFLUXDB_HOST", 0)
    monkeypatch.setenv("INFLUXDB_USER", 0)
    monkeypatch.setenv("INFLUXDB_USER_PASSWORD", 0)
    monkeypatch.setenv("INFLUXDB_DB", 0)

    from os_credits.main import create_app

    app = await create_app()
    client = await test_client(app)
    resp = await client.get("/ping")
    text = await resp.text()
    assert resp.status == 200 and text == "Pong", "/ping endpoint failed"
