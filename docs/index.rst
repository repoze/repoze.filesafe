Documentation for repoze.filesafe
=================================

Overview
--------

:mod:`repoze.filesafe` provides utilities methods to handle creation
of files on the filesystem safely by integrating with the ``ZODB`` package's
transaction manager.  It can be used in combination with `repoze.tm`_ (or
`repoze.tm2`_) for use in WSGI environments.

.. _repoze.tm: http://pypi.python.org/pypi/repoze.tm
.. _repoze.tm2: http://docs.repoze.org/tm2/


Purpose and Usage
-----------------

The ZODB transaction manager is a completely generic transaction
manager.  It can be used independently of the actual "object database"
part of ZODB, for example to integrate the transaction handling of SQL
servers with your application. :mod:`repoze.filesafe` allows you to
create files within a transaction. If the transaction is aborted
the files will be removed, prevention any leftovers from polluting
your disk.

Creating a file works very similar to the standard python `open`
call:

.. code-block:: python

    from repoze.filesafe import create

    f=create("/some/path", "rb")
    f.write("Hello, World!")
    f.close()

This will create a new temporary file and write your data to it. Once the
transaction is commited it will move the file to the path name you specified.

.. note::

  The :mod:`repoze.filesafe` middleware has to be in the WSGI pipeline. If
  you use its API without using the middleware any created files will
  not be moved into place.


Adding :mod:`repoze.filesafe` To Your WSGI Pipeline
---------------------------------------------------

Via ``PasteDeploy`` .INI configuration::

  [pipeline:main]
   pipeline =
           egg:repoze.tm2#tm
           myapp

Via Python:

.. code-block:: python

  from otherplace import mywsgiapp

  from repoze.filesafe import FileSafeMiddleware
  new_wsgiapp = FileSafeMiddleware(mywsgiapp)



Contacting
----------

The `repoze-dev maillist
<http://lists.repoze.org/mailman/listinfo/repoze-dev>`_ should be used
for communications about this software.  Put the overview of the
purpose of the package here.


.. toctree::
   :maxdepth: 2

   changes


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
