PYTHON ?= python3.12

.PHONY: help install run run-v2 run-legacy test test-v2-voice lint clean

help:
	@echo "GAIA V2 multilingual AI chatbot"
	@echo ""
	@echo "  make install   create venv and install dependencies"
	@echo "  make run       start the new GAIA V2 app on http://localhost:8000"
	@echo "  make run-legacy start the original Flask app on http://localhost:5000"
	@echo "  make test      run core tests (offline)"
	@echo "  make clean     remove caches and logs"

install:
	@test -x ./venv/bin/python || $(PYTHON) -m venv venv
	@./venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 12), "GAIA requires a Python 3.12 virtual environment"'
	./venv/bin/python -m pip install pip==26.2.1
	./venv/bin/python -m pip install -r requirements.lock

run:
	./venv/bin/python app.py

run-v2:
	./venv/bin/python -m uvicorn backend.main:app --port 8000

run-legacy:
	./venv/bin/python app.py --legacy

test:
	./venv/bin/python -m pytest -q tests

test-browser:
	./venv/bin/python tests/test_browser.py

test-v2-voice:
	./venv/bin/python scripts/verify_voice_input.py

lint:
	./venv/bin/python -m py_compile app.py config.py src/*.py backend/*.py tests/*.py scripts/*.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache logs/*.log
