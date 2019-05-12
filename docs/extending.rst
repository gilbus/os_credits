Extending
=========

.. contents:: Contents

The following sections of this guide will show you how to extend the *OpenStack Credits
Service* by additional *metrics*, *Perun* attributes or models to store inside the
*InfluxDB*.

New Metric
----------

Adding a new metric to the billing process does also mean adding a new measurement, see
:ref:`Metrics and Measurements`.

New TotalUsageMetric
^^^^^^^^^^^^^^^^^^^^

Read the page linked above and the master thesis mentioned in the main page for a full
explanation, but in short: If the ``value`` of your measurement encodes something like
*total usage{time,counter} of x* this is the correct choice. Copy the structure of one
of the existing :class:`~os_credits.credits.base_models.TotalUsageMetric` subclasses,
modify the ``CREDITS_PER_VIRTUAL_HOUR`` to your liking, that's it.

Other type of metric
^^^^^^^^^^^^^^^^^^^^

.. todo:: write and implement
