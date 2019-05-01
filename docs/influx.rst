InfluxDB interaction
====================

We interact with the *InfluxDB* in multiple ways:

* It is using our ``/write`` endpoint to mirror the data stored by *Prometheus* which is
  why we do not have to pull regularly to receive new usage measurements, this data are
  provided in the `InfluxDB Line Protocol
  <https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/>`_
* We use it to store our :class:`~os_credits.credits.models.BillingHistory` objects,
  writing objects requires to encode them in the *Line Protocol*

We are therefore required to parse and construct the *Line Protocol*, which is why we
cannot only use the functionality of the ``aioinflux`` package, on which our
:class:`~os_credits.influx.client.InfluxDBClient` is based.

InfluxDB Line Protocol
----------------------

The following syntax example is taken from the official documentation
::

    weather,location=us-midwest temperature=82 1465839830100400200
      |    -------------------- --------------  |
      |             |             |             |
      |             |             |             |
    +-----------+--------+-+---------+-+---------+
    |measurement|,tag_set| |field_set| |timestamp|
    +-----------+--------+-+---------+-+---------+

InfluxDBPoint
-------------

.. autoclass:: os_credits.influx.model.InfluxDBPoint
   :members:
   :undoc-members:
