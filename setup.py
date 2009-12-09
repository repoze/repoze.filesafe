from ez_setup import use_setuptools
use_setuptools()

__version__ = '1.0a5'

import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

setup(name='repoze.filesafe',
      version=__version__,
      description='Transaction-aware file creation',
      long_description=README + "\n\n" + CHANGES,
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        ],
      keywords='transaction wsgi repoze',
      author="Wichert Akkerman",
      author_email="repoze-dev@lists.repoze.org",
      url="http://docs.repoze.org/filesafe/",
      license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
      packages=find_packages(),
      include_package_data=True,
      namespace_packages=['repoze'],
      zip_safe=False,
      install_requires=['transaction', 'setuptools'],
      test_suite = "repoze.filesafe.tests",
      entry_points="""
      [paste.filter_factory]
      filesafe = repoze.filesafe:filesafe_filter_factory

      [paste.filter_app_factory]
      filesafe = repoze.filesafe:filesafe_filter_app_factory
      """,
      )

