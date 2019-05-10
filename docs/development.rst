Development Guide
=================

The chapters of this guide will show you how to extend the *OpenStack Credits Service*
by additional *metrics*, *Perun* attributes or models to store inside the *InfluxDB*.
Other pages describe why certain styles have been chosen.

.. toctree::
   :maxdepth: 2
   :caption: Contents:


Subclass Hooks
--------------

Inheritance has been used whenever it seemed useful to share code and functionality
among multiple subclasses. If we want all subclasses to be registered, e.g.
:class:`~os_credits.perun.base_attributes.PerunAttribute`, or checked for correctness,
e.g. :class:`~os_credits.perun.notifications.EmailNotificationBase`, we use
:func:`~object.__init_subclass__`. If defined on a base class it gets called whenever
subclass if **defined**, not when it is **constructed**. This mechanism also allows for
passing variables.

.. doctest::

   >>> class A:
   ...   def __init_subclass__(cls, foo):
   ...      print(f"{cls.__name__}'s foo: {foo}")
   >>> class B(A, foo='bar'):
   ...     pass
   B's foo: bar

This feature is also used to register new metrics as they are all subclasses of
:class:`~os_credits.credits.base_models.Metric`.
