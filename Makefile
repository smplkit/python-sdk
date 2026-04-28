VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install generate test lint \
	config_runtime_showcase config_management_showcase \
	flags_runtime_showcase flags_management_showcase \
	logging_runtime_showcase logging_management_showcase \
	management_showcase

install:
	$(PIP) install -e '.[dev]'

generate:
	bash scripts/generate.sh

test:
	$(PYTHON) -m pytest --cov=smplkit --cov-report=term-missing

lint:
	$(PYTHON) -m ruff check src/ tests/

config_runtime_showcase: install
	$(PYTHON) examples/config_runtime_showcase.py

config_management_showcase: install
	$(PYTHON) examples/config_management_showcase.py

flags_runtime_showcase: install
	$(PYTHON) examples/flags_runtime_showcase.py

flags_management_showcase: install
	$(PYTHON) examples/flags_management_showcase.py

logging_runtime_showcase: install
	$(PYTHON) examples/logging_runtime_showcase.py

logging_management_showcase: install
	$(PYTHON) examples/logging_management_showcase.py

management_showcase: install
	$(PYTHON) examples/management_showcase.py
