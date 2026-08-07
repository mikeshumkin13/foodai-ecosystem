PYTHON ?= python3

.PHONY: test lint check

test:
	$(PYTHON) scripts/check_project_memory.py

lint:
	$(PYTHON) -c "import ast, pathlib; ast.parse(pathlib.Path('scripts/check_project_memory.py').read_text(encoding='utf-8'))"

check: lint test
