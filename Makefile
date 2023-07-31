.PHONY: lint cover clean

PY_COVER := python3 -m coverage
PROGRAM := docstrex.py


clean:
	rm -f $(PROGRAM),cover
	rm -f $(PROGRAM)-n,cover

lint:
	mypy $(PROGRAM)
	pydocstyle $(PROGRAM)
	flake8 --max-line-length=100 $(PROGRAM)

test:
	echo "Running unit tests"
	pydocstyle --unit-test

cover: clean lint test
	echo "Running test coverage"
	rm -f $(PROGRAM),cover $(PROGRAM),cover-n
	$(PY_COVER) erase
	$(PY_COVER) run --append $(PROGRAM) --unit-test > /dev/null
	$(PY_COVER) annotate
	$(PY_COVER) report
	cat -n $(PROGRAM),cover >> $(PROGRAM),cover-n
	grep "! " $(PROGRAM),cover-n

