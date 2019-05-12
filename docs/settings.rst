Settings
========

Consider storing all settings inside a ``.env`` file at the root of the repository. This
file is included in the ``.gitignore`` and referenced by multiple make targets, e.g.
``make docker-run-dev``. Use ``.default.env`` as a reference whose values are
coordinated with the ``project_usage`` repository.

.. automodule:: os_credits.settings

.. autoclass:: Config
