.PHONY: install test lint run

install:
	pip install -r requirements.txt

test:
	python -m pytest

lint:
	black .
	flake8 .

run:
	python main.py
