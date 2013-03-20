import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

version = '2.0b2'

setup(name='repoze.filesafe',
      version=version,
      description='Transaction-aware file creation',
      long_description=README + "\n\n" + CHANGES,
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        ],
      keywords='transaction wsgi repoze',
      author="Wichert Akkerman",
      author_email="repoze-dev@lists.repoze.org",
      url="http://docs.repoze.org/filesafe/",
      license="BSD-derived (http://www.repoze.org/LICENSE.txt)",
      packages=find_packages('src'),
      package_dir={'': 'src'},
      include_package_data=True,
      namespace_packages=['repoze'],
      zip_safe=False,
      install_requires=['transaction', 'six'],
      test_suite = "repoze.filesafe",
      entry_points="""
      [paste.filter_factory]
      filesafe = repoze.filesafe:filesafe_filter_factory

      [paste.filter_app_factory]
      filesafe = repoze.filesafe:filesafe_filter_app_factory
      """,
      )
