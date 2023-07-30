.PHONY: lint cover clean

PY_COVER := python3 -m coverage
PROGRAM := docstrex.py


lint:
	mypy $(PROGRAM)
	pydocstyle $(PROGRAM)
	flake8 --max-line-length=100 $(PROGRAM)

cover:
	echo "Running test coverage"
	rm -f $(PROGRAM),cover
	$(PY_COVER) erase
	$(PY_COVER) run --append $(PROGRAM) --unit-test > /dev/null
	$(PY_COVER) annotate
	$(PY_COVER) report

clean:
	rm -f $(PROGRAM),cover

test:
	echo "Running unit tests"
	pydocstyle --unit-test
