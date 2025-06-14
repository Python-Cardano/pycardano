.PHONY: cov cov-html clean clean-test clean-pyc clean-build qa format test test-single help docs
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := poetry run python -c "$$BROWSER_PYSCRIPT"

ensure-pure-cbor2: ## ensures cbor2 is installed with pure Python implementation
	@poetry run python -c "from importlib.metadata import version; \
	print(version('cbor2'))" > .cbor2_version
	@poetry run python -c "import cbor2, inspect; \
	print('Checking cbor2 implementation...'); \
	decoder_path = inspect.getfile(cbor2.CBORDecoder); \
	using_c_ext = decoder_path.endswith('.so'); \
	print(f'Implementation path: {decoder_path}'); \
	print(f'Using C extension: {using_c_ext}'); \
	exit(1 if using_c_ext else 0)" || \
	(echo "Reinstalling cbor2 with pure Python implementation..." && \
	poetry run pip uninstall -y cbor2 && \
	CBOR2_BUILD_C_EXTENSION=0 poetry run pip install --no-binary cbor2 "cbor2==$$(cat .cbor2_version)" --force-reinstall && \
	rm .cbor2_version)

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

cov: ensure-pure-cbor2 ## check code coverage
	poetry run pytest -n 4 --cov pycardano

cov-html: cov ## check code coverage and generate an html report
	poetry run coverage html -d cov_html
	$(BROWSER) cov_html/index.html


clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -f .coverage
	rm -fr cov_html/
	rm -fr .pytest_cache

test: ensure-pure-cbor2 ## runs tests
	poetry run pytest -vv -n 4

test-integration: ## runs integration tests
	cd integration-test && ./run_tests.sh

test-single: ## runs tests with "single" markers
	poetry run pytest -s -vv -m single

qa: ensure-pure-cbor2 ## runs static analyses
	poetry run flake8 pycardano
	poetry run mypy --install-types --non-interactive pycardano
	poetry run black --check .

format: ## runs code style and formatter
	poetry run isort .
	poetry run black .

docs: ## build the documentation
	pipx inject poetry poetry-plugin-export
	poetry export --dev --without-hashes > docs/requirements.txt
	rm -r -f docs/build
	poetry run sphinx-build docs/source docs/build/html
	$(BROWSER) docs/build/html/index.html

release: clean qa test format ensure-pure-cbor2 ## build dist version and release to pypi
	poetry build
	poetry publish