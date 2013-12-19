PYTHON		:= python

all:: check

bin/buildout: 
	$(PYTHON) bootstrap.py

bin/python bin/nosetests bin/sphinx-build:  bin/buildout buildout.cfg versions.cfg
	bin/buildout
	touch bin/python
	touch bin/sphinx-build
	touch bin/nosetests

# This breaks on Python 3
#check:: bin/sphinx-build
#	$(MAKE) -C docs linkcheck

check:: bin/nosetests
	bin/nosetests

docs: bin/sphinx-build
	$(MAKE) -C docs html

htmlcov: bin/nosetests
	bin/nosetests \
		--with-coverage \
		--cover-package=repoze.filesafe \
		--cover-branches \
		--cover-html

jenkins: bin/nosetests bin/sphinx-build
	# $(MAKE) -C docs linkcheck
	bin/nosetests \
		--with-xunit --xunit-file=junit.xml \
		--with-coverage \
		--cover-package=repoze.filesafe \
		--cover-branches \
		--cover-xml

.PHONY: all check docs jenkins htmlcov
