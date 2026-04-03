.PHONY: install generate test lint config_showcase flags_management_showcase flags_runtime_showcase

install:
	pip install -e '.[dev]'

generate:
	bash scripts/generate.sh

test:
	pytest --cov=smplkit --cov-report=term-missing

lint:
	ruff check src/ tests/

config_showcase: install
	python examples/config_showcase.py

flags_management_showcase: install
	python examples/flags_management_showcase.py

flags_runtime_showcase: install
	python examples/flags_runtime_showcase.py
