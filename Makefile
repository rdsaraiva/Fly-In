PYTHON = python3
MAP = maps/example.txt

.PHONY: install run debug clean lint lint-strict

install:
	$(PYTHON) -m pip install flake8 mypy

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -prune -exec rm -rf {} +
	rm -rf .mypy_cache

lint:
	flake8 *.py
	mypy *.py --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 *.py
	mypy *.py --strict

# Level 2 (animation): disabled
# animate:
# 	$(PYTHON) main.py $(MAP) --animate
