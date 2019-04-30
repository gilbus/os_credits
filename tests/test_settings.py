from decimal import Decimal
from importlib import reload


def test_parsing_special_values(monkeypatch):
    from os_credits import settings

    "Test whether values from environment variables are parsed and stored correctly"
    integer_conf_value = 98
    list_conf_value = {"ProjectA", "ProjectB"}
    monkeypatch.setenv(
        "OS_CREDITS_PROJECT_WHITELIST", ";".join(sorted(list_conf_value))
    )
    monkeypatch.setenv("INFLUXDB_PORT", str(integer_conf_value))
    monkeypatch.setenv("OS_CREDITS_PRECISION", str(3))
    # necessary to pickup changed environment variables
    reload(settings)
    from os_credits.settings import config

    assert (
        config["OS_CREDITS_PROJECT_WHITELIST"] == list_conf_value
    ), "Comma-separated list was not parsed correctly from environment"
    assert (
        config["INFLUXDB_PORT"] == integer_conf_value
    ), "Integer value was not parsed/converted correctly from environment"
    assert config["OS_CREDITS_PRECISION"] == Decimal(10) ** -3


def test_bad_int_values(monkeypatch):
    from os_credits import settings

    bad_test_port = -324
    monkeypatch.setenv("INFLUXDB_PORT", str(bad_test_port))
    reload(settings)
    from os_credits.settings import config

    assert (
        config["INFLUXDB_PORT"] != bad_test_port
    ), "Negative int value from environment was not ignored"
    assert config["INFLUXDB_PORT"] != str(
        bad_test_port
    ), "Bad integer value was not removed from environment and is still accessible due to the Chainmap"

    invalid_int_value = "lala"
    monkeypatch.setenv("INFLUXDB_PORT", invalid_int_value)
    reload(settings)
    from os_credits.settings import config

    assert (
        config["INFLUXDB_PORT"] != invalid_int_value
    ), "Negative int value from environment was not ignored"
