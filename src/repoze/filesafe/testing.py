from six import BytesIO
from six import StringIO
from zope.interface import implementer
from transaction.interfaces import IDataManager
from six import reraise
import errno


# MockFileMixIn must not be derived from object, or the closed attributed
# from StringIO will disappear in Python 2. This unfortuantely means we can
# also not use super(), so we need the _base attribute with the base class.
class MockFileMixin:
    def close(self):
        self.mockdata = self.getvalue()
        self._base.close(self)

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_value is not None:
            reraise(exc_type, exc_value, traceback)

    def __enter__(self):
        return self


class MockBytesIO(MockFileMixin, BytesIO):
    _base = BytesIO


class MockStringIO(MockFileMixin, StringIO):
    _base = StringIO


@implementer(IDataManager)
class DummyDataManager:

    def __init__(self, tempdir=None):
        self.tempdir = tempdir
        self.in_commit = False
        self.data = {}
        self.vault = {}

    def _exists(self, path):
        return path in self.data

    def _unlink(self, path):
        if path not in self.data:
            raise OSError(
                errno.ENOENT,
                "[Errno 2] No such file or directory: '%s'" % path)
        del self.data[path]

    def _link(self, src, link_name):
        if src not in self.data:
            raise OSError(
                errno.ENOENT,
                "[Errno 2] No such file or directory: '%s'" % src)
        self.data[link_name] = self.data[src]

    def _rename(self, src, dst):
        if src not in self.data:
            raise OSError(
                errno.ENOENT,
                "[Errno 2] No such file or directory: '%s'" % src)
        self.data[dst] = self.data[src]
        del self.data[src]

    def _renames(self, src, dst):
        if src not in self.data:
            raise OSError(
                errno.ENOENT,
                "[Errno 2] No such file or directory: '%s'" % src)
        self.data[dst] = self.data[src]
        del self.data[src]

    def create_file(self, path, mode):
        if path in self.vault:
            if self.vault[path].get('deleted', False):
                del self.vault[path]
            else:
                raise ValueError("%s is already taken", path)
        tmppath = "tmp%s" % path
        self.data[tmppath] = file = MockBytesIO() if 'b' in mode else MockStringIO()
        self.vault[path] = dict(tempfile=tmppath)
        return file

    def rename_file(self, src, dst, recursive=False):
        if dst in self.vault:
            if self.vault[dst].get('deleted', False):
                del self.vault[dst]
            else:
                raise ValueError("%s is already taken", dst)
        if src not in self.vault and not self._exists(src):
            raise OSError(
                errno.ENOENT,
                "[Errno 2] No such file or directory: '%s'" % src)
        self.vault[dst] = dict(tempfile=src, source=src,
            moved=True, has_original=False, recursive=recursive)
        self.vault[src] = dict(tempfile=src, destination=dst,
            moved=True, has_original=self._exists(src), recursive=recursive)

    def open_file(self, path, mode="r"):
        cls = MockBytesIO if 'b' in mode else MockStringIO
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise IOError(
                        "[Errno 2] No such file or directory: '%s'" % path)
            file = self.data[info["tempfile"]]
            if file.closed:
                return cls(file.mockdata)
            else:
                return file
        else:
            if path not in self.data:
                return open(path, mode)
            file = self.data[path]
            if file.closed:
                return cls(file.mockdata)
            else:
                return file

    def delete_file(self, path):
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise OSError(errno.ENOENT,
                        "[Errno 2] No such file or directory: '%s'" % path)
            try:
                self._unlink(info["tempfile"])
            except OSError:
                # XXX log.exception makes the testruns die with an exception
                # in multiprocessing.util:258
                #log.exception("Failed to delete temporary file %s", target)
                pass
            del self.vault[path]
        else:
            if not self._exists(path):
                raise OSError(errno.ENOENT,
                        "[Errno 2] No such file or directory: '%s'" % path)
            self.vault[path] = dict(tempfile=path, deleted=True)

    def file_exists(self, path):
        if path in self.vault:
            info = self.vault[path]
            deleted = info.get('deleted', False)
            moved = info.get('moved', False) and 'destination' in info
            return not (deleted or moved)
        return self._exists(path)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        self.in_commit = True
        for target in self.vault:
            info = self.vault[target]
            if info.get('moved', False) and 'destination' in info:
                continue
            if info.get("deleted", False):
                self._rename(target, "%s.filesafe" % target)
                info["has_original"] = True
                info["moved"] = True
            else:
                if self._exists(target):
                    info["has_original"] = True
                    self._link(target, "%s.filesafe" % target)
                else:
                    info["has_original"] = False
                rename = self._renames if info.get("recursive") else self._rename
                rename(info["tempfile"], target)
                info["moved"] = True

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("deleted", False):
                try:
                    self._unlink("%s.filesafe" % info["tempfile"])
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to remove file backup for %s",
                    # target)
                    pass
            elif info.get("has_original"):
                try:
                    self._unlink("%s.filesafe" % target)
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to remove file backup for %s",
                    # target)
                    pass

        self.in_commit = False
        self.vault.clear()

    def tpc_abort(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("moved"):
                try:
                    if info["has_original"]:
                        self._rename("%s.filesafe" % target, target)
                    elif 'source' in info:
                        rename = self._renames if info.get("recursive") else self._rename
                        rename(target, info["source"])
                    else:
                        self._unlink(target)
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to restore original file %s",
                    # target)
                    pass
            else:
                try:
                    self._unlink(info["tempfile"])
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to delete temporary file %s",
                    # target)
                    pass

        self.in_commit = False
        self.vault.clear()

    abort = tpc_abort


def setup_dummy_data_manager():
    """Setup a dummy datamanager.

    This datamanager will not make any changes on the filesystem; instead it
    creates in-memory files and returns those to the caller. The created files
    can be found in the `data` attribute of the returned data manager.
    """
    import repoze.filesafe
    repoze.filesafe._local.manager = mgr = DummyDataManager()
    return mgr


def cleanup_dummy_data_manager():
    """Remove a dummy datamanger, if installed.

    The manager is returned, allowing tests to introspect the created files via
    the `data` attribute of the returned data manager.
    """
    import repoze.filesafe
    manager = getattr(repoze.filesafe._local, 'manager', None)
    if isinstance(manager, DummyDataManager):
        del repoze.filesafe._local.manager
    return manager
