# OS Credits

Process the usage values exported by a [`usage
exporter`](https://github.com/gilbus/OS_project_usage_exporter), calculate the used
'credits' for any group according to them and store the results in appropriate fields
inside [*Perun*](https://perun-aai.org/).

## Running

The service is integrated into the docker-compose setup of
[`project_usage`](https://github.com/deNBI/project_usage), please refer to its wiki for
setup instructions.

## Developing

The project and its dependencies are managed via
[*Poetry*](https://pypi.org/project/poetry/), so you'll have to install it and then
execute `poetry install` to get up and running. To run the code use the provided
`Dockerfile.dev` and integrate it into the `project_usage` stack:

1. Stop the original `portal_credits` container (and optionally remove it from the
   `docker-compose stack` to prevent it from launching accidentally)
2. Build the development container via `docker build -f Dockerfile.dev -t credits-dev
   .`
3. Start it
	```bash
	docker run --publish=8000:80 --name portal_credits --network \
	project_usage_portal -v $PWD/os_credits:/code/os_credits:ro -v \
	$PWD/config:/code/config:ro credits-dev
	```
The container is using the `adev runserver` command from the
[`aiohttp-devtools`](https://github.com/aio-libs/aiohttp-devtools) which will restart
your app on any code change. But since the code is bind mounted inside the container you
can simply continue editing and have it restart on any change.

### Monitoring/Debugging

If the application misbehaves and you would like to set a lower log level or get stats
**without restarting** it you have two possibilities:

1. Use the `/logconfig` endpoint to change the logging settings of the running
   application, by first editing or providing a `credits.toml` file and then uploading
   it via `http`, but you can of course just use `curl`. All commands are available
   after `poetry install`
	```bash
	IP_ADDR="$( docker inspect --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' portal_credits)"
	toml2json -i config/credits.toml | jq '.logging' | http $IP_ADDR/logconfig
	```
2. Query the `/stats` endpoint, optionally with `?verbose=1`

## Tests

Tests are written against [`pytest`](https://pytest.org) and can be executed from the
project directory via `python -m pytest`, respectively `poetry run python -m pytest`.
