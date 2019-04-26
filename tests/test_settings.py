from importlib import reload


async def test_settings(monkeypatch):
    from os_credits import settings

    "Test whether values from environment variables are parsed and stored correctly"
    integer_conf_value = 98
    list_conf_value = {"ProjectA", "ProjectB"}
    monkeypatch.setenv(
        "OS_CREDITS_PROJECT_WHITELIST", ";".join(sorted(list_conf_value))
    )
    monkeypatch.setenv("OS_CREDITS_PRECISION", str(integer_conf_value))
    # necessary to pickup changed environment variables
    reload(settings)
    from os_credits.settings import config

    assert (
        list_conf_value == config["OS_CREDITS_PROJECT_WHITELIST"]
    ), "Comma-separated list was not parsed correctly from environment"
    assert (
        integer_conf_value == config["OS_CREDITS_PRECISION"]
    ), "Integer value was not parsed/converted correctly from environment"
