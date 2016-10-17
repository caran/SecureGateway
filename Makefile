.PHONY: clean-pyc clean-build docs clean

DATE_STRING:=$(shell /bin/date +"%Y-%m-%d")

help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "clean-doc - remove documentation artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests suitable for an embedded Linux machine"
	@echo "test-graphical - run tests for graphical components (requires dependencies, see docs)"
	@echo "test-all - run all tests"
	@echo "vcan - Start Linux virtual CAN bus vcan0"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "pdf - generate PDF documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package TODO!!!"
	@echo "install - install the package to the active Python's site-packages"
	@echo "develop - install the package as symlinks, for development"
	@echo "undevelop - uninstall the package as symlinks (for development)"

clean: clean-build clean-pyc clean-test clean-doc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	rm -fr .idea/
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -f .coverage.*
	rm -fr htmlcov/
	find . -name 'temporary-*.txt' -exec rm -fr {} +

clean-doc:
	rm -fr docs/_build
	rm -f .coverage
	rm -f .coverage.*
	rm -fr htmlcov/
	-$(MAKE) -C docs clean

lint:
	flake8 sgframework tests

test:
	python3 setup.py test   # tests.suites.embedded

test-graphical:
	python3 tests/suites.py -s graphical

test-all:
	python3 tests/suites.py -s alltests

coverage:
	@echo "    "
	@echo "NOTE: In order to measure coverage also for programs started via subprocess,"
	@echo "you need to modify your sitecustomize.py file (typically in /etc/pythonX.Y)."
	@echo "    "
	rm -f .coverage
	rm -f .coverage.*
	coverage run --rcfile=tests/coveragerc tests/suites.py -s alltests
	coverage combine
	coverage report -m
	coverage html
	@echo "    "
	@echo "    "
	@echo "    "
	@echo "Opening web browser ..."
	xdg-open htmlcov/index.html

docs: clean-doc
	$(MAKE) -C docs html
	@echo "    "
	@echo "    "
	@echo "    "
	@echo "Opening web browser ..."
	xdg-open docs/_build/html/index.html

pdf: docs
	$(MAKE) -C docs latexpdf
	cp -f docs/_build/latex/sgframework.pdf docs/_build/sgframework_$(DATE_STRING).pdf;
	@echo "    "
	@echo "    "
	@echo "    "
	@echo "Opening PDF reader ..."
	xdg-open docs/_build/latex/sgframework.pdf

vcan:
	modprobe vcan
	ip link add dev vcan0 type vcan
	ifconfig vcan0 up

release: clean
	python3 setup.py sdist upload
	python3 setup.py bdist_wheel upload

dist: clean
	python3 setup.py sdist
	python3 setup.py bdist_wheel
	ls -l dist

install: clean
	python3 setup.py install

subscribe:
	@echo "    "
	@echo "    "
	mosquitto_sub -v -t +/#

develop: clean
	python3 setup.py develop

undevelop: clean
	python3 setup.py develop --uninstall
	@echo "    "
	@echo "    "
	@echo "You need to manually uninstall any scripts (see setup.py). For example:"
	@echo "    sudo rm /usr/local/bin/canadapter  "
	@echo "    sudo rm /usr/local/bin/servicemanager  "
