Documentation for repoze.tm2 (``repoze.tm`` fork)
=================================================

Overview
--------

:mod:`repoze.tm2` is WSGI middleware which uses the ``ZODB`` package's
transaction manager to wrap a call to its pipeline children inside a
transaction.

.. note:: :mod:`repoze.tm2` is equivalent to the :mod:`repoze.tm`
   package (it was forked from :mod:`repoze.tm`), except it has a
   dependency only on the ``transaction`` package rather than a
   dependency on the entire ``ZODB3`` package (``ZODB3`` 3.8 ships
   with the ``transaction`` package right now).  It is an error to
   install both repoze.tm and repoze.tm2 into the same environment, as
   they provide the same entry points and import points.

Behavior
--------

When this middleware is present in the WSGI pipeline, a new
transaction will be started once a WSGI request makes it to the
:mod:`repoze.tm` middleware.  If any downstream application raises an
exception, the transaction will be aborted, otherwise the transaction
will be committed.  Any "data managers" participating in the
transaction will be aborted or committed respectively.  A ZODB
"connection" is an example of a data manager.

Since this is a tiny wrapper around the ZODB transaction module, and
the ZODB transaction module is "thread-safe" (in the sense that its
default policy is to create a new transaction for each thread), it
should be fine to use in either multiprocess or multithread
environments.

Purpose and Usage
-----------------

The ZODB transaction manager is a completely generic transaction
manager.  It can be used independently of the actual "object database"
part of ZODB.  One of the purposes of creating :mod:`repoze.tm` was to
allow for systems other than Zope to make use of two-phase commit
transactions in a WSGI context.

Let's pretend we have an existing system that places data into a
relational database when someone submits a form.  The system has been
running for a while, and our code handles the database commit and
rollback for us explicitly; if the form processing succeeds, our code
commits the database transaction.  If it fails, our code rolls back
the database transaction.  Everything works fine.

Now our customer asks us if we can also place data into another
separate relational database when the form is submitted as well as
continuing to place data in the original database.  We need to put
data in both databases, and if we want to ensure that no records exist
in one that don't exist in the other as a result of a form submission,
we're going to need to do a pretty complicated commit and rollback
dance in each place in our code which needs to write to both data
stores.  We can't just blindly commit one, then commit the other,
because the second commit may fail and we'll be left with "orphan"
data in the first, and we'll either need to clean it up manually or
leave it there to trip over later.

A transaction manager helps us ensure that no data is committed to
either database unless both participating data stores can commit.
Once the transaction manager determines that both data stores are
willing to commit, it will commit them both in very quick succession,
so that there is only a minimal chance that the second data store will
fail to commit.  If it does, the system will raise an error that makes
it impossible to begin another transaction until the system restarts,
so the damage is minimized.  In practice, this error almost never
occurs unless the code that interfaces the database to the transaction
manager has a bug.

Adding :mod:`repoze.tm` To Your WSGI Pipeline
---------------------------------------------

Via ``PasteDeploy`` .INI configuration::

  [pipeline:main]
   pipeline =
           egg:repoze.tm2#tm
           myapp

Via Python:

.. code-block:: python

  from otherplace import mywsgiapp

  from repoze.tm import TM
  new_wsgiapp = TM(mywsgiapp)

Mocking Up A Data Manager
-------------------------

The piece of code you need to write in order to participate in ZODB
transactions is called a 'data manager'.  It is typically a class.
Here's the interface that you need to implement in the code for a data
manager:

.. code-block:: python

    class IDataManager(zope.interface.Interface):
        """Objects that manage transactional storage.

        These objects may manage data for other objects, or they
        may manage non-object storages, such as relational
        databases.  For example, a ZODB.Connection.

        Note that when some data is modified, that data's data
        manager should join a transaction so that data can be
        committed when the user commits the transaction.  """

        transaction_manager = zope.interface.Attribute(
            """The transaction manager (TM) used by this data
            manager.

            This is a public attribute, intended for read-only
            use.  The value is an instance of ITransactionManager,
            typically set by the data manager's constructor.  """
            )

        def abort(transaction):
            """Abort a transaction and forget all changes.

            Abort must be called outside of a two-phase commit.

            Abort is called by the transaction manager to abort transactions
            that are not yet in a two-phase commit.
            """

        # Two-phase commit protocol.  These methods are called by
        # the ITransaction object associated with the transaction
        # being committed.  The sequence of calls normally follows
        # this regular expression: tpc_begin commit tpc_vote
        # (tpc_finish | tpc_abort)

        def tpc_begin(transaction):

            """Begin commit of a transaction, starting the
            two-phase commit.

            transaction is the ITransaction instance associated with the
            transaction being committed.
            """

        def commit(transaction):

            """Commit modifications to registered objects.

            Save changes to be made persistent if the transaction
            commits (if tpc_finish is called later).  If tpc_abort
            is called later, changes must not persist.

            This includes conflict detection and handling.  If no
            conflicts or errors occur, the data manager should be
            prepared to make the changes persist when tpc_finish
            is called.  """

        def tpc_vote(transaction):
            """Verify that a data manager can commit the transaction.

            This is the last chance for a data manager to vote 'no'.  A
            data manager votes 'no' by raising an exception.

            transaction is the ITransaction instance associated with the
            transaction being committed.
            """

        def tpc_finish(transaction):

            """Indicate confirmation that the transaction is done.

            Make all changes to objects modified by this
            transaction persist.

            transaction is the ITransaction instance associated
            with the transaction being committed.

            This should never fail.  If this raises an exception,
            the database is not expected to maintain consistency;
            it's a serious error.  """

        def tpc_abort(transaction):

            """Abort a transaction.

            This is called by a transaction manager to end a
            two-phase commit on the data manager.  Abandon all
            changes to objects modified by this transaction.

            transaction is the ITransaction instance associated
            with the transaction being committed.

            This should never fail.
            """

        def sortKey():

            """Return a key to use for ordering registered
            DataManagers.

            ZODB uses a global sort order to prevent deadlock when
            it commits transactions involving multiple resource
            managers.  The resource manager must define a
            sortKey() method that provides a global ordering for
            resource managers.  """
            # Alternate version:
            #"""Return a consistent sort key for this connection.
            # #This allows ordering multiple connections that use
            the same storage in #a consistent manner. This is
            unique for the lifetime of a connection, #which is
            good enough to avoid ZEO deadlocks.  #"""

Let's implement a mock data manager.  Our mock data manager will write
data to a file if the transaction commits.  It will not write data to
a file if the transaction aborts:

.. code-block:: python

    class MockDataManager:

        transaction_manager = None

        def __init__(self, data, path):
            self.data = data
            self.path = path

        def abort(self, transaction):
            pass

        def tpc_begin(self, transaction):
            pass

        def commit(self, transaction):
            import tempfile
            self.tempfn = tempfile.mktemp()
            temp = open(self.tempfn, 'wb')
            temp.write(self.data)
            temp.flush()
            temp.close()

        def tpc_vote(self, transaction):
            import os
            if not os.path.exists(self.tempfn):
                raise ValueError('%s doesnt exist' % self.tempfn)
            if os.path.exists(self.path):
                raise ValueError('file already exists')

        def tpc_finish(self, transaction):
            import os
            os.rename(self.tempfn, self.path)

        def tpc_abort(self, transaction):
            import os
            try:
                os.remove(self.tempfn)
            except OSError:
                pass

We can create a datamanager and join it into the currently running
transaction:

.. code-block:: python

    dm = MockDataManager('heres the data',  '/tmp/file')
    import transaction
    t = transaction.get()
    t.join(dm)

When the transaction commits, a file will be placed in '/tmp/file'
containing 'heres the data'.  If the transaction aborts, no file will
be created.

If more than one data manager is joined to the transaction, all of
them must be willing to commit or the entire transaction is aborted
and none of them commit.  If you can imagine creating two of the mock
data managers we've made within application code, if one has a problem
during "tpc_vote", neither will actually write a file to the ultimate
location, and thus your application consistency is maintained.

Integrating Your Data Manager With :mod:`repoze.tm`
---------------------------------------------------

The :mod:`repoze.tm` transaction management machinery has an implicit
policy.  When it is in the WSGI pipeline, a transaction is started
when the middleware is invoked.  Thus, in your application code,
calling "import transaction; transaction.get()" will return the
transaction object created by the :mod:`repoze.tm` middleware.  You
needn't call t.commit() or t.abort() within your application code.
You only need to call t.join, to register your data manager with the
transaction.  :mod:`repoze.tm` will abort the transaction if an
exception is raised by your application code or lower middleware
before it returns a WSGI response.  If your application or lower
middleware raises an exception, the transaction is aborted.

Cleanup
-------

When a :mod:`repoze.tm` is in the WSGI pipeline, a boolean key is
present in the environment (``repoze.tm.active``).  A utility function
named isActive can be imported from the :mod:`repoze.tm` package and
passed the WSGI environment to check for activation:

.. code-block:: python

    from repoze.tm import isActive
    tm_active = isActive(wsgi_environment)

If an application needs to perform an action after a transaction ends,
the "after_end" registry may be used to register a callback.  The
after_end.register function accepts a callback (accepting no
arguments) and a transaction instance:

.. code-block:: python

    from repoze.tm import after_end
    import transaction
    t = transaction.get() # the current transaction
    def func():
        pass # close a connection, etc
    after_end.register(func, t)

"after_end" callbacks should only be registered when the transaction
manager is active, or a memory leak will result (registration cleanup
happens only on transaction commit or abort, which is managed by
:mod:`repoze.tm` while in the pipeline).

Further Documentation
---------------------

Many database adapters written for Zope (e.g. for Postgres, MySQL,
etc) use this transaction manager, so it should be possible to take a
look in these places to see how to implement a more real-world
transaction-aware database connector that uses this module in non-Zope
applications:

- http://svn.zope.org/ZODB/branches/3.7/src/transaction/

- http://svn.zope.org/ZODB/branches/3.8/src/transaction/

- http://mysql-python.sourceforge.net/ (ZMySQLDA)

- http://www.initd.org/svn/psycopg/psycopg2/trunk/ (ZPsycoPGDA)

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
