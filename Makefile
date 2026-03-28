.PHONY: install generate test lint

install:
	pip install -e '.[dev]'

generate:
	bash scripts/generate.sh

test:
	pytest --cov=smplkit --cov-report=term-missing

lint:
	ruff check src/ tests/
