repoze.tm2 (Transaction Manager)
===============================

Middleware which uses the ZODB transaction manager to wrap a call to
its pipeline children inside a transaction.  This is a fork of the
``repoze.tm`` package which depends only on the ``transaction``
package rather than the entirety of ZODB (for users who don't rely on ZODB).

See docs/index.rst for documentation.
