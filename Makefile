PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
IMAGE ?= adaptedge
TAG ?= local

.PHONY: install lint test evaluate build run smoke deploy clean

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

lint:
	$(VENV)/bin/ruff check src tests

test:
	$(VENV)/bin/pytest -q --cov=adaptedge --cov-report=term-missing

evaluate:
	$(PY) -m adaptedge.evaluate --runs 200 --seed 42 --out reports/metrics.json

build:
	nerdctl build --tag $(IMAGE):$(TAG) --tag $(IMAGE):latest .

run:
	nerdctl run --rm -p 127.0.0.1:18080:8000 $(IMAGE):$(TAG)

smoke:
	./scripts/smoke_test.sh $(IMAGE):$(TAG) adaptedge-smoke 18080

deploy:
	./deploy/deploy.sh $(IMAGE):$(TAG)

clean:
	rm -rf $(VENV) reports .pytest_cache .ruff_cache src/*.egg-info
