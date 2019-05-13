Endpoints
=========
All of our endpoints are defined in :mod:`os_credits.views` and connected at
:ref:`Startup`. The docstrings of the functions may look mangled when interpreted as
``rst`` in Sphinx since they are ``yaml`` which is parsed by `aiohttp-swagger
<https://aiohttp-swagger.readthedocs.io>`_.

Costs per Hour
--------------
.. autofunction:: os_credits.views.costs_per_hour
   :noindex:

Credits History
---------------
We store all billing transactions inside the *InfluxDB*.

.. autoclass:: os_credits.credits.models.BillingHistory
   :noindex:
   :members:
   :show-inheritance:

A rudimentary visualization of a project's credits history can be seen unter
``/credits_history/{project_name}``.

Swagger
-------
All of our API endpoints are documented with swagger annotations which can be seen and
executed under ``/api/doc``. Use the ``docker-run-dev`` target of the :ref:`Makefile`
and visit it under `<http://localhost:8000/api/doc>`_

InfluxDB Write
--------------
This endpoint is automatically used by *InfluxDB* when mirroring its stored data to
`subscribers
<https://docs.influxdata.com/influxdb/v1.7/administration/subscription-management>`_.
The corresponding function is :func:`~os_credits.views.influxdb_write`.
