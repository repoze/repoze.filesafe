from StringIO import StringIO
from zope.interface import implements
from transaction.interfaces import IDataManager


class MockFile(StringIO):
    def close(self):
        self.mockdata = self.getvalue()
        return StringIO.close(self)


class DummyDataManager:
    implements(IDataManager)

    def __init__(self, tempdir=None):
        self.tempdir=tempdir
        self.data={}

    def createFile(self, path, mode):
        self.data[path]=file=MockFile()
        return file

    def openFile(self, path, mode="r"):
        if path in self.data:
            file = self.data[path]
            if file.closed:
                return MockFile(file.mockdata)
            else:
                return file
        else:
            return open(path, mode)



def setupDummyDataManager():
    """Setup a dummy datamanager. This datamanager will not make any changes
    on the filesystem; instead it creates in-memory files and returns those
    to the caller. The created files can be found in the `data` attribute of
    the returned data manager.
    """
    import repoze.filesafe
    repoze.filesafe._local.vault=mgr=DummyDataManager()
    return mgr


def cleanupDummyDataManager():
    """Remove a dummy datamanger, if installed. The manager is returned,
    allowing tests to introspect the created files via the `data` attribute of
    the returned data manager.
    """
    import repoze.filesafe
    vault=getattr(repoze.filesafe._local, "vault", None)
    if isinstance(vault, DummyDataManager):
        del repoze.filesafe._local.vault
    return vault

