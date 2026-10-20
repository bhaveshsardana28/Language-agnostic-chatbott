.PHONY: help install bootstrap-model run run-v2 run-legacy test test-v2-voice lint clean

help:
	@echo "Language-Agnostic Chatbot (pivot translation + single English intent model)"
	@echo ""
	@echo "  make install   create venv and install dependencies"
	@echo "  make bootstrap-model  build the local campus intent model if missing"
	@echo "  make run       start the new GAIA V2 app on http://localhost:8000"
	@echo "  make run-legacy start the original Flask app on http://localhost:5000"
	@echo "  make test      run core tests (offline)"
	@echo "  make clean     remove caches and logs"

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.lock
	@$(MAKE) bootstrap-model

bootstrap-model:
	@if [ -f models/intent_classifier.joblib ]; then echo "intent model already present"; else ./venv/bin/python scripts/train.py >/dev/null; echo "intent model generated"; fi

run:
	./venv/bin/python app.py

run-v2:
	./venv/bin/python -m uvicorn backend.main:app --port 8000

run-legacy:
	./venv/bin/python app.py --legacy

test:
	./venv/bin/python -m pytest -q tests/test_core.py tests/test_v2.py tests/test_code_switching.py tests/test_rag_qa.py tests/test_persistence.py tests/test_ocr.py

test-browser:
	./venv/bin/python tests/test_browser.py

test-v2-voice:
	./venv/bin/python scripts/verify_voice_input.py

lint:
	./venv/bin/python -m py_compile app.py config.py src/*.py backend/*.py tests/*.py scripts/*.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache logs/*.log
