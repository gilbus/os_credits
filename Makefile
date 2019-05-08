HOST=127.0.0.1
PORT=8080
DOCKER_USERNAME=$(USER)
DOCKER_IMAGENAME=os_credits

.PHONY: clean-pyc docker-build docker-build-dev docker-run docs test test-online test-online-only mypy coverage lint run run-dev
rule all:
	@echo 'Please provide a Phony target'

clean-pyc:
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +
	find . -type d -name '__pycache__' -prune -exec rm -rf {} \;
	rm -rf .mypy_cache

clean-build:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

docker-build:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} \;
	poetry run bin/build_docker.py -u $(DOCKER_USERNAME) -i $(DOCKER_IMAGENAME)

docker-build-dev:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} \;
	docker build -f Dockerfile.dev -t os_credits-dev .

docker-run-dev:
	docker stop portal_credits || true
	docker rm portal_credits || true
	docker run \
		--publish=8000:80 \
		--name portal_credits \
		--network project_usage_portal \
		--volume $(PWD)/src:/code/src:ro \
		--env-file .env \
		--detach \
		os_credits-dev:latest

docs:
	cd docs && $(MAKE) html

# sleep is necessary to wait until launched services are ready
test:
	poetry run docker-compose -f tests/docker-compose.yml up --detach
	sleep 5
	poetry run pytest --color=yes tests src
	poetry run docker-compose -f tests/docker-compose.yml down --volumes --remove-orphans

test-online:
	env TEST_ONLINE=1 $(MAKE) test

test-online-only:
	poetry run env TEST_ONLINE=1 pytest --color=yes --no-cov tests/test_perun.py

mypy:
	poetry run mypy src/os_credits --html-report=htmlcov/mypy

run:
	poetry run os-credits --port $(PORT) --host $(HOST)

run-dev:
	poetry run adev runserver --port $(PORT) --host $(HOST) src/os_credits 

setup:
	poetry install
	poetry run pre-commit install -t pre-commit
	poetry run pre-commit install -t pre-push
