from six import StringIO
from zope.interface import implementer
from transaction.interfaces import IDataManager
from six import reraise


class MockFile(StringIO):
    def close(self):
        self.mockdata = self.getvalue()
        return StringIO.close(self)

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_value is not None:
            reraise(exc_type, exc_value, traceback)

    def __enter__(self):
        return self


@implementer(IDataManager)
class DummyDataManager:

    def __init__(self, tempdir=None):
        self.tempdir = tempdir
        self.in_commit = False
        self.data = {}
        self.vault = {}

    def createFile(self, path, mode):
        if path in self.vault:
            if self.vault[path].get('deleted', False):
                del self.vault[path]
            else:
                raise ValueError("%s is already taken", path)
        tmppath = "tmp%s" % path
        self.data[tmppath] = file = MockFile()
        self.vault[path] = dict(tempfile=tmppath)
        return file

    def openFile(self, path, mode="r"):
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise IOError(
                        "[Errno 2] No such file or directory: '%s'" % path)
            file = self.data[info["tempfile"]]
            if file.closed:
                return MockFile(file.mockdata)
            else:
                return file
        else:
            if path not in self.data:
                return open(path, mode)
            file = self.data[path]
            if file.closed:
                return MockFile(file.mockdata)
            else:
                return file

    def deleteFile(self, path):
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise OSError(
                        "[Errno 2] No such file or directory: '%s'" % path)
            del self.data[info["tempfile"]]
            del self.vault[path]
        else:
            self.vault[path] = dict(tempfile=path, deleted=True)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        self.in_commit = True
        for target in self.vault:
            info = self.vault[target]
            if target in self.data:
                info["has_original"] = True
                self.data["%s.filesafe" % target] = self.data[target]
            else:
                info["has_original"] = False
            self.data[target] = self.data[info["tempfile"]]
            del self.data[info["tempfile"]]
            info["moved"] = True

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("has_original"):
                try:
                    del self.data["%s.filesafe" % target]
                except KeyError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to remove file backup for %s",
                    # target)
                    pass

        self.vault.clear()
        self.in_commit = False

    def tpc_abort(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("moved"):
                try:
                    if info["has_original"]:
                        oldname = "%s.filesafe" % target
                        self.data[target] = self.data[oldname]
                        del self.data[oldname]
                    else:
                        del self.data[target]
                except KeyError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to restore original file %s",
                    # target)
                    pass
            else:
                try:
                    del self.data[info["tempfile"]]
                except KeyError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to delete temporary file %s",
                    # target)
                    pass

        self.vault.clear()
        self.in_commit = False

    abort = tpc_abort


def setupDummyDataManager():
    """Setup a dummy datamanager. This datamanager will not make any changes
    on the filesystem; instead it creates in-memory files and returns those
    to the caller. The created files can be found in the `data` attribute of
    the returned data manager.
    """
    import repoze.filesafe
    repoze.filesafe._local.manager = mgr = DummyDataManager()
    return mgr


def cleanupDummyDataManager():
    """Remove a dummy datamanger, if installed. The manager is returned,
    allowing tests to introspect the created files via the `data` attribute of
    the returned data manager.
    """
    import repoze.filesafe
    manager = getattr(repoze.filesafe._local, 'manager', None)
    if isinstance(manager, DummyDataManager):
        del repoze.filesafe._local.manager
    return manager
