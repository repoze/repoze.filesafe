repoze.tm (Transaction Manager)

Overview

  Middleware which uses the ZODB transaction manager to wrap a call to
  its pipeline children inside a transaction.

Behavior

  When this middleware is present in the WSGI pipeline, a new
  transaction will be started once a WSGI request makes it to the
  repoze.tm middleware.  If any downstream application raises an
  exception, the transaction will be aborted, otherwise the
  transaction will be committed.  Any "resource managers"
  participating in the transaction will be aborted or committed
  respectively.  A ZODB "connection" is an example of a resource
  manager.

  Since this is a tiny wrapper around the ZODB transaction module, and
  the ZODB transaction module is "thread-safe" (in the sense that its
  default policy is to create a new transaction for each thread), it
  should be fine to use in either multiprocess or multithread
  environments.

Developing

  When a repoze.tm is in the WSGI pipeline, a boolean key is present
  in the environment ('repoze.tm.active').  A utility function named
  isActive can be imported from the repoze.tm package and passed the
  WSGI environment to check for activation::

    from repoze.tm import isActive
    tm_active = isActive(wsgi_environment)

  If an application needs to perform an action after a transaction ends,
  the "after_end" registry may be used to register a callback.  The
  after_end.register function accepts a callback (accepting no
  arguments) and a transaction instance::

    from repoze.tm import after_end
    import transaction
    t = transaction.get() # the current transaction
    def func():
        pass # close a connection, etc
    after_end.register(func, t)

  'after_end' callbacks should only be registered when the transaction
  manager is active, or a memory leak will result (registration cleanup
  happens only on transaction commit or abort, which is managed by
  repoze.tm while in the pipeline).

Notes

  The ZODB transaction manager is a completely generic transaction
  manager.  It can be used independently of the actual "object
  database" part of ZODB.  Its documentation is not very good, alas,
  but many database adapters written for Zope (e.g. for Postgres,
  MySQL, etc) use this transaction manager, so it should be possible
  to take a look in these places to see how to implement a
  transaction-aware database connector that uses this module in
  non-Zope applications::

    http://svn.zope.org/ZODB/branches/3.7/src/transaction/

    http://svn.zope.org/ZODB/branches/3.8/src/transaction/

    http://mysql-python.sourceforge.net/ (ZMySQLDA)

    http://www.initd.org/svn/psycopg/psycopg2/trunk/ (ZPsycoPGDA)

Contacting

  The "repoze-dev
  maillist":http://lists.repoze.org/mailman/listinfo/repoze-dev should
  be used for communications about this software.
