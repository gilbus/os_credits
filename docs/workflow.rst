Billing Workflow
================
Again, the whole process is more explained in-depth inside the master thesis linked on
the main page. This page's main purpose is to link to other parts of this documentation
explaining the processes in more detail.

.. contents:: Contents

Startup
-------

#.
   .. autofunction:: os_credits.main.create_app
      :noindex:

#. Wait for the :ref:`InfluxDB Write` endpoint to receive Influx Line items which are
   put into the :ref:`Task Queue` and processed by :ref:`Task Workers`.
#. Run

Group Locks
-----------
Since we are an *asynchronous* service multiple task are processed at the same time, a
task switch happens whenever we have to wait for an external resource. For example a
database or a remote api.

To make sure that no Group/Project is billed by two tasks at the same time we are using
:class:`~asyncio.Lock` instances stored inside a :func:`~collections.defaultdict`
accessed by the group's name which is unique inside *de.NBI*. **No information must be**
exchanged with *Perun* by a task unless it holds the *Lock* of its group. Using a
defaultdict automatically creates a new Lock whenever a new group occurs.

Task Queue
----------
Every InfluxDB line sent to the :ref:`InfluxDB Write` endpoint is put into this queue
and processed by :ref:`Task Workers`. It is an :class:`asyncio.Queue`.

Task Workers
------------
Created in :func:`~os_credits.main.create_worker`.

Creation
^^^^^^^^
.. autofunction:: os_credits.credits.tasks.worker
   :noindex:

Processing
^^^^^^^^^^
#.
   .. autofunction:: os_credits.credits.tasks.process_influx_line
      :noindex:
#.
   .. autofunction:: os_credits.credits.tasks.update_credits
      :noindex:
