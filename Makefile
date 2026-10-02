.PHONY: help install run test lint clean

help:
	@echo "Language-Agnostic Chatbot (pivot translation + single English intent model)"
	@echo ""
	@echo "  make install   create venv and install dependencies"
	@echo "  make run       start the Flask app on http://localhost:5000"
	@echo "  make test      run core tests (offline)"
	@echo "  make clean     remove caches and logs"

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run:
	./venv/bin/python app.py

run-v2:
	./venv/bin/python -m uvicorn backend.main:app --port 8000

test:
	./venv/bin/python tests/test_core.py
	./venv/bin/python tests/test_v2.py
	./venv/bin/python tests/test_code_switching.py

test-browser:
	./venv/bin/python tests/test_browser.py

lint:
	./venv/bin/python -m py_compile app.py config.py src/*.py tests/*.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache logs/*.log
