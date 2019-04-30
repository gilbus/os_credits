OpenStack Credits Service
=========================

This service is responsible for processing the usage measurements exported by a
```usage exporter`` <https://github.com/gilbus/OS_project_usage_exporter>`__,
calculate the used ‘credits’ for any group according to them and store
the results in appropriate fields inside
`Perun <https://perun-aai.org/>`__.

Running
-------

The service is integrated into the docker-compose setup of
```project_usage`` <https://github.com/deNBI/project_usage>`__, please
refer to its wiki for setup instructions.

Configuration
-------------

Take a look at ``.default.env`` to see all possible configuration
variables. Copy it over to ``.env`` (included in ``.gitignore``) and
insert your values. The latter will be used automatically, i.e. by
``make docker-run``.

Monitoring/Debugging
~~~~~~~~~~~~~~~~~~~~

If the application misbehaves and you would like to set a lower log
level or get stats **without restarting** it you have two possibilities:

1. Use the ``/logconfig`` endpoint to change the logging settings of the
   running application.
2. Query the ``/stats`` endpoint, optionally with ``?verbose=true``

Building
--------

Use the provided ``Makefile`` via ``make build-docker``. This will build
``$USER/os_credits`` and use the version of the project as version of
the image. To modify this values call
``make build-docker DOCKER_USERNAME=<your_username>``.

Developing
----------

The project and its dependencies are managed via
`Poetry <https://pypi.org/project/poetry/>`__, so you’ll have to install
it and then execute ``poetry install`` to get up and running. Your first
action should be ``poetry run pre-commit install`` to install
`Pre-Commit Hooks <https://pre-commit.com/>`__, to make sure that every
of your commits results in a running application.

Stack integration
~~~~~~~~~~~~~~~~~

To run the code use the provided ``Dockerfile.dev`` which you can build
via ``make docker-build-dev``. Afterward use ``make docker-run`` to
integrate the development container into the ``project_usage`` stack.

The development container is using the ``adev runserver`` command from
the
```aiohttp-devtools`` <https://github.com/aio-libs/aiohttp-devtools>`__
which will restart your app on any code change. But since the code is
bind mounted inside the container you can simply continue editing and
have it restart on any change.

Tests
~~~~~

Tests are written against ```pytest`` <https://pytest.org>`__ and can be
executed from the project directory via ``make test``.

Security Tests
~~~~~~~~~~~~~~

Those are handled by ```bandit`` <https://bandit.readthedocs.io>`__, run
them via ``poetry run bandit --ini .bandit -r``.
