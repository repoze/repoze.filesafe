__version__ = '0.1'

import os
from setuptools import setup, find_packages

setup(name='repoze.tm',
      version=__version__,
      description='Zope-like transaction manager via WSGI middleware',
      long_description=""" Long description XXX """,
      classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Zope Public License",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Framework :: Zope3",
        ],
      keywords='web application server wsgi zope',
      author="Agendaless Consulting",
      author_email="repoze-dev@lists.repoze.org",
      dependency_links=['http://dist.repoze.org'],
      url="http://www.repoze.org",
      license="ZPL 2.0",
      packages=find_packages(),
      include_package_data=True,
      namespace_packages=['repoze'],
      zip_safe=False,
      install_requires=['ZODB3 >= 3.8.0b3'],
      test_suite = "repoze.tm.tests",
      entry_points="""
      [paste.filter_app_factory]
      tm = repoze.tm:make_tm
      """,
      )

