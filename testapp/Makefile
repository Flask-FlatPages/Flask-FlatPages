.PHONY: bootstrap clean distclean manage pep8 server shell test

PROJECT = flask_flatpages
APP = .

ENV ?= env
VENV = $(shell python -c 'import sys; print(int(hasattr(sys, "real_prefix")));')

ifeq ($(VENV),1)
	NOSETESTS = nosetests
	PEP8 = flake8
	PIP = pip
	PYTHON = python
else
	NOSETESTS = $(ENV)/bin/nosetests
	PEP8 = $(ENV)/bin/flake8
	PIP = $(ENV)/bin/pip
	PYTHON = $(ENV)/bin/python
endif

COVERAGE_DIR ?= /tmp/$(PROJECT)-coverage
SERVER_HOST ?= 0.0.0.0
PORT ?= 8302
TEST_ARGS ?= -v

bootstrap:
	bootstrapper -e $(ENV)/ -C "{pip} install ipython==2.4.0"

clean:
	find .. -name "*.pyc" -delete
	find .. -name __pycache__ -type d -exec rm -rf {} 2> /dev/null +

distclean: clean
	rm -f ../MANIFEST .coverage
	rm -rf ../build/ ../dist/ ../.tox/ ../*.egg*/ $(ENV)/

manage:
	$(PYTHON) ./manage.py $(COMMAND)

pep8:
	$(PEP8) --statistics ../$(PROJECT)/ $(APP)/*.py

shell:
	COMMAND=shell $(MAKE) manage

server:
	COMMAND="runserver -t $(SERVER_HOST) -p $(PORT)" $(MAKE) manage

test: clean pep8
	$(NOSETESTS) --logging-clear-handler $(TEST_ARGS) -w $(APP)/ \
	--with-coverage --cover-branches --cover-package=../$(PROJECT)/ \
	--cover-html --cover-html-dir=$(COVERAGE_DIR)
