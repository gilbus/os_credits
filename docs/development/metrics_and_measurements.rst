Metrics and Measurements
------------------------

The terms *Metric* and *Measurement* are often used interchangeably, but for our service
a *Measurement* is a :class:`~dataclasses.dataclass` which is a subclass of
UsageMeasurement_ that holds all data but does not contain any logic to bill and a
*Metric* is a subclass of Metric_ which gets attached to a UsageMeasurement_ and holds
information and functionality on how to bill its usage value.

Metric
^^^^^^

As of now all implemented metrics only bill based on the raw usage value of a
measurement since those contain the amount of time a resource has been in use, such as
:class:`~os_credits.credits.models.VCPUMetric` or
:class:`~os_credits.credits.models.RAMMetric`.

.. inheritance-diagram:: os_credits.credits.models.VCPUMetric os_credits.credits.models.RAMMetric
   :parts: 1

.. autoclass:: os_credits.credits.base_models.Metric
   :members:


.. _UsageMeasurement: :class:`~os_credits.credits.base_models.UsageMeasurement`
.. _Metric: :class:`~os_credits.credits.base_models.Metric`
