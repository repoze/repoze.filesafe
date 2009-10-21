Documentation for repoze.filesafe
=================================

Overview
--------

:mod:`repoze.filesafe` provides utilities methods to safely handle creation of
files on the filesystem by integrating with the ``ZODB`` package's transaction
manager.  It can be used in combination with `repoze.tm`_ (or `repoze.tm2`_)
for use in WSGI environments. More information about using a transaction
manager can be found in the 
`Using a Transaction-Aware Data Manager Under repoze.tm`_ article.

.. _repoze.tm: http://pypi.python.org/pypi/repoze.tm
.. _repoze.tm2: http://docs.repoze.org/tm2/
.. _Using a Transaction-Aware Data Manager Under repoze.tm: http://repoze.org/tmdemo.html


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

    from repoze.filesafe import createFile

    f=createFile("/some/path", "w")
    f.write("Hello, World!")
    f.close()

This will create a new temporary file and write your data to it. Once the
transaction is commited it will move the file to the path name you specified.
If the transaction is aborted the temporary file will be removed.

:mod:`repoze.filesafe` assumes that temporary files will be on the same
filesystem as the target path. The default location is determined by
the python :mod:`tempfile` module. You may need to configure a different path
if you use a separate filesystem for `/tmp` using the `TMPDIR` environment
variable.


Unit tests
----------
:mod:`repoze.filesafe.testing` provides several utility methods to facilitate
unit testing of code which uses :mod:`repoze.filesafe`:

.. autofunction:: repoze.filesafe.testing.setupDummyDataManager

.. autofunction:: repoze.filesafe.testing.cleanupDummyDataManager


Adding :mod:`repoze.filesafe` To Your WSGI Pipeline
---------------------------------------------------

Via ``PasteDeploy`` .INI configuration::

  [pipeline:main]
  pipeline =
      egg:repoze.tm2#tm
      myapp

Or via Python:

.. code-block:: python

  from otherplace import mywsgiapp
  from repoze.filesafe import FileSafeMiddleware

  new_wsgiapp = FileSafeMiddleware(mywsgiapp)


Manually integrate with :mod:`transaction`
------------------------------------------

If you are not using a WSGI environment you will need to create a
:obj:`FileSafeDataManager` instance and join it to the current transaction:

.. code-block:: python

   import transaction
   from repoze.filesafe import FileSafeDataManager

   tx=transaction.get()
   tx.join(FileSafeDataManager())

:obj:`FileSafeDataManager` is not thread safe. If you use multiple threads
make sure to use a separate instance for every thread.


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

