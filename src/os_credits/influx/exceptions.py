"""Contains exceptions to wrap the one used by the ``aioinflux`` package.
"""


class InfluxDBError(Exception):
    "Wrapper around :exc:`aioinflux.client.InfluxDBError` in our functions."
    pass
