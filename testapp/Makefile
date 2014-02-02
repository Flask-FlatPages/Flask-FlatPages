.PHONY: bootstrap clean distclean docs list_updates manage pep8 server shell test

PROJECT = flask_flatpages
APP = .

ENV ?= env
VENV = $(shell python -c 'import sys; print(1 if hasattr(sys, "real_prefix") else 0);')

ifeq ($(VENV),1)
	FLAKE8 = flake8
	NOSETESTS = nosetests
	PIP = pip
	PYTHON = python
else
	FLAKE8 = $(ENV)/bin/flake8
	NOSETESTS = $(ENV)/bin/nosetests
	PIP = $(ENV)/bin/pip
	PYTHON = $(ENV)/bin/python
endif

COVERAGE_DIR ?= /tmp/$(PROJECT)-coverage
SERVER_HOST ?= 0.0.0.0
PORT ?= 8302
TEST_ARGS ?= -v

bootstrap:
	bootstrapper -e $(ENV)/ -C "{pip} install ipython==1.1.0"

clean:
	find .. -name "*.pyc" -delete
	rm -rf ../$(PROJECT)/__pycache__/

distclean: clean
	rm -rf ../build/ ../dist/ ../.tox/ ../*.egg*/ $(ENV)/
	rm -f ../MANIFEST .coverage

docs:
	$(PIP) install Sphinx==1.2.1

list_updates:
	$(PIP) list -lo

manage:
	$(PYTHON) ./manage.py $(COMMAND)

pep8:
	$(FLAKE8) --statistics ../$(PROJECT)/ $(APP)/*.py

shell:
	COMMAND=shell $(MAKE) manage

server:
	COMMAND="runserver -t $(SERVER_HOST) -p $(PORT)" $(MAKE) manage

test: clean pep8
	$(NOSETESTS) --logging-clear-handler $(TEST_ARGS) -w $(APP)/ \
	--with-coverage --cover-branches --cover-package=../$(PROJECT)/ \
	--cover-html --cover-html-dir=$(COVERAGE_DIR)
