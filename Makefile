.PHONY: install generate test lint \
	config_runtime_showcase config_management_showcase \
	flags_runtime_showcase flags_management_showcase \
	logging_runtime_showcase logging_management_showcase

install:
	pip install -e '.[dev]'

generate:
	bash scripts/generate.sh

test:
	pytest --cov=smplkit --cov-report=term-missing

lint:
	ruff check src/ tests/

config_runtime_showcase: install
	python examples/config_runtime_showcase.py

config_management_showcase: install
	python examples/config_management_showcase.py

flags_runtime_showcase: install
	python examples/flags_runtime_showcase.py

flags_management_showcase: install
	python examples/flags_management_showcase.py

logging_runtime_showcase: install
	python examples/logging_runtime_showcase.py

logging_management_showcase: install
	python examples/logging_management_showcase.py
