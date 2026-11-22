.DEFAULT_GOAL := help
.PHONY: help venv install run typecheck test test-unit \
	test-integration cov bench build check clean

# Environment & Platform Configuration
ifeq ($(OS),Windows_NT)
    BOOT_PY  ?= python
    VENV_BIN := .venv/Scripts
else
    BOOT_PY  ?= python3
    VENV_BIN := .venv/bin
endif

PY      := $(VENV_BIN)/python
PROFILE ?= examples/profiles/flaky.toml

## Display available targets and their descriptions
help:
	@awk '/^## /{desc=substr($$0,4); next} \
		/^[a-zA-Z_-]+:/{if(desc!=""){split($$0,a,":"); printf "  \033[36m%-18s\033[0m %s\n", a[1], desc} desc=""; next} \
		{desc=""}' $(MAKEFILE_LIST)

# Internal file target to track virtual environment creation
.venv/pyvenv.cfg:
	$(BOOT_PY) -m venv .venv

## Create the local Python virtual environment
venv: .venv/pyvenv.cfg

## Install the package in editable mode with dev dependencies
install: venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

## Start the proxy and control plane using the active profile
run:
	$(PY) -m chaostap --profile $(PROFILE)

## Run strict static type checking via mypy
typecheck:
	$(PY) -m mypy

## Execute the full test suite
test:
	$(PY) -m pytest

## Execute unit tests only
test-unit:
	$(PY) -m pytest tests/unit

## Execute integration tests only
test-integration:
	$(PY) -m pytest tests/integration -m integration

## Run tests with terminal and HTML coverage reports
cov:
	$(PY) -m pytest --cov --cov-report=term-missing --cov-report=html

## Run proxy latency and overhead benchmarks
bench:
	$(PY) benchmarks/overhead.py

## Build source distribution (sdist) and wheel packages
build:
	$(PY) -m pip install --upgrade build
	$(PY) -m build

## Run full CI validation pipeline (lint, typecheck, and tests)
check: typecheck test

## Remove build artifacts, caches, coverage reports, and local SQLite DBs
clean:
	rm -rf build dist htmlcov .coverage .pytest_cache .mypy_cache
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -f *.db *.db-wal *.db-shm
