.PHONY: test test-e2e lint format

test:
	python -m pytest

test-e2e:
	python -m pytest -m e2e

lint:
	ruff check .

format:
	ruff format .
