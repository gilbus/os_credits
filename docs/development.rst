Development Guide
=================
.. contents:: Contents

Developing
----------
Makefile
^^^^^^^^

All frequently required development commands are provided by the ``Makefile`` in the
root folder of the repository. It provides the following commands.

.. program-output:: make -C .. help

Pre-Commit Hooks
^^^^^^^^^^^^^^^^
`Pre-Commit hooks <https://pre-commit.com/>`_ define commands to run when certain files
are modified by a commit. They are invoked whenever ``git commit`` is invoked. For
example, ``make test`` is always executed when a ``*.py`` file has changed to make sure
that every commit results in a runnable application. Take a look at
``.pre-commit-config.yaml``.

Tests
^^^^^
Tests are written against `pytest <https://pytest.org>`_ and can be
executed from the project directory via ``make <test_mode>``, see :ref:`Makefile`.

Separating tests into online and offline tests has two reasons:

#. In case of frequent commits do not continuously query *Perun* and more important
#. In case of offline development (or bad connection, e.g. on mobile) the tests would
   always fail

But to make sure that committed code does always pass all integrations tests inside
``tests/test_application`` they are run against an offline backend emulating *Perun*.
These tests the whole workflow of the application including multiple corner cases which
is why they must succeed with every commit, see :ref:`Pre-Commit Hooks`.

Whenever commits that modified any ``*.py`` file are pushed all tests against the
*Perun* API are run exclusively since the attempt to push should indicate that we are
online.

The ``tests`` directory does contain Unit and Integrations tests, in combination with
:ref:`Subclass Hooks` even classes that are not integrated anywhere are tested.

Type Hints
^^^^^^^^^^
(Optional) Type hints are so awesome that I decided to make them kind of non-optional
for this project since they are able to catch **so much** errors before you even run any
code! Take a look at the `Type hints cheat sheet
<https://mypy.readthedocs.io/en/latest/cheat_sheet_py3.html>`_ for an introduction or
examine the existing code. The execution of ``mypy`` is part of the :ref:`Pre-Commit
Hooks`, not only against the actual code but also against the tests. This makes sure
that the tests are implemented correctly which is an obvious requirement to have a
proper test base.

Codestyle
^^^^^^^^^
It's all `Black <https://black.readthedocs.io>`_. Enforced via :ref:`Pre-Commit Hooks`.

Current ToDos
^^^^^^^^^^^^^
.. todolist::

Python
------
This section contains the explanations of used programming patterns/python techniques.

Subclass Hooks
^^^^^^^^^^^^^^
Inheritance has been used whenever it seemed useful to share code and functionality
among multiple subclasses. If we want all subclasses to be registered, e.g.
:class:`~os_credits.perun.base_attributes.PerunAttribute`, or checked for correctness,
e.g. :class:`~os_credits.perun.notifications.EmailNotificationBase`, we use
:meth:`~object.__init_subclass__`. If defined on a base class it gets called whenever
a subclass if **defined**, not when it is **constructed**. This mechanism also allows
for passing variables.

.. doctest::

   >>> class A:
   ...   def __init_subclass__(cls, foo):
   ...      print(f"{cls.__name__}'s foo: {foo}")
   >>> class B(A, foo='bar'):
   ...     pass
   B's foo: bar

This feature is also used to register new metrics as they are all subclasses of
:class:`~os_credits.credits.base_models.Metric`.

Documentation
-------------
Try to leave documentation as possible inside the code next to its functionality to
(hopefully) prevent documentation and code to get separated. Use `doctests
<file:///usr/share/doc/python/html/library/doctest.html>`_ if possible.
