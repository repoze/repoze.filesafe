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

    from repoze.filesafe import create_file

    f = create_file("/some/path", "w")
    f.write("Hello, World!")
    f.close()

This will create a new temporary file and write your data to it. Once the
transaction is commited it will move the file to the path name you specified.
If the transaction is aborted the temporary file will be removed.

:mod:`repoze.filesafe` assumes that temporary files will be on the same
filesystem as the target path. The default location is determined by
the python :mod:`tempfile` module. You may need to configure a different path
if you use a separate filesystem for `/tmp` using the `TMPDIR` environment
variable. Alternatively, `create_file` accepts a third parameter `tempdir`,
which is `None` by default, to allow you to specify a temporary directory
for :mod:`tempfile` module to use.


It is possible to (re)open a file that has not been been commited yet using
the `open_file` method:

.. code-block:: python

    from repoze.filesafe import create_file, open_file

    f = create_file("/some/path", "w")
    f.write("Hello, World!")
    f.close()

    f = open_file("/some/path")
    print f.read()
    f.close()

This will print the greeting that was stored in the file. If `open_file` is
called with a path that has not been created using `create_file` in the current
transaction it will be opened normally, as if the standard `open` method was
used.

You can also delete files with `delete_file` as well as rename or move files
using `rename_file`.


Unit tests
----------
:mod:`repoze.filesafe.testing` provides several utility methods to facilitate
unit testing of code which uses :mod:`repoze.filesafe`:

.. autofunction:: repoze.filesafe.testing.setup_dummy_data_manager

.. autofunction:: repoze.filesafe.testing.cleanup_dummy_data_manager


Integration :mod:`repoze.filesafe` with transactions
----------------------------------------------------

Earlier repoze.filesafe versions required usage of a WSGI middleware or manual
hooking into the transaction logic. Since repoze.filesafe 2 this is no longer
required.

The WSGI middleware is still available for backwards compatibility, but no
longer does anything.



Contacting
----------

This project is managed as a `github project
<https://github.com/repoze/repoze.filesafe>`_. 


.. toctree::
   :maxdepth: 2

   changes


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

