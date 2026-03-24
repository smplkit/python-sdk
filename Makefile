.PHONY: generate test lint

generate:
	bash scripts/generate.sh

test:
	pytest --cov=smplkit --cov-report=term-missing

lint:
	ruff check src/ tests/
