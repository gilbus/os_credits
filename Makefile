HOST=127.0.0.1
PORT=8080

clean-pyc:
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +
	find . -type d -prune -name '__pycache__' -exec rm -rf {} \;
	rm -rf .mypy_cache

clean-build:
	rm --force --recursive build/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

build-docker:
	find . -type d -prune -name '__pycache__' -exec rm -rf {} \;
	bin/build_docker.py


test:
	poetry run python -m pytest -v --color=yes

lint:
	flake8 --exclude=.tox

run:
	poetry run os-credits --port $(PORT) --host $(HOST)
