PYTHON		:= python

all:: check

bin/buildout: 
	$(PYTHON) bootstrap.py

bin/python bin/test bin/sphinx-build:  bin/buildout buildout.cfg versions.cfg
	bin/buildout

check:: bin/sphinx-build
	$(MAKE) -C docs linkcheck

check:: bin/test
	bin/test

docs: bin/sphinx-build
	$(MAKE) -C docs html

jenkins: bin/test bin/sphinx-build
	$(MAKE) -C docs linkcheck
	bin/coverage run --branch --include='src/repoze/filesafe/*' bin/test --xml

.PHONY: all check docs jenkins
