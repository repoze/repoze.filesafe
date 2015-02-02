import errno
import logging
import os.path
import tempfile
from zope.interface import implementer
from transaction.interfaces import IDataManager

log = logging.getLogger("repoze.filesafe")


@implementer(IDataManager)
class FileSafeDataManager:

    transaction_manager = None

    def __init__(self, tempdir=None):
        self.tempdir = tempdir
        self.in_commit = False
        self.vault = {}

    def _cleanup(self):
        from repoze.filesafe import _remove_manager
        self.vault.clear()
        _remove_manager()

    def create_file(self, path, mode):
        if path in self.vault:
            if self.vault[path].get('deleted', False):
                del self.vault[path]
            else:
                raise ValueError("%s is already taken", path)
        try:
            file = tempfile.NamedTemporaryFile(mode=mode, dir=self.tempdir,
                    delete=False)
        except TypeError:
            # Python pre-2.6 does not support the delete option, so play
            # some tricks to prevent our file from disappearing.
            file = tempfile.NamedTemporaryFile(mode=mode, dir=self.tempdir)
            file.unlink = lambda x: x

        self.vault[path] = dict(tempfile=file.name)
        return file

    def rename_file(self, src, dst, recursive=False):
        if dst in self.vault:
            if self.vault[dst].get('deleted', False):
                del self.vault[dst]
            else:
                raise ValueError("%s is already taken", dst)
        self.vault[dst] = dict(tempfile=src, source=src,
            moved=True, has_original=False, recursive=recursive)

    def open_file(self, path, mode="r"):
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise IOError(
                        "[Errno 2] No such file or directory: '%s'" % path)
            return open(info["tempfile"], mode)
        else:
            return open(path, mode)

    def delete_file(self, path):
        if path in self.vault:
            info = self.vault[path]
            if info.get('deleted', False):
                raise OSError(errno.ENOENT,
                        "[Errno 2] No such file or directory: '%s'" % path)
            try:
                os.unlink(info["tempfile"])
            except OSError:
                # XXX log.exception makes the testruns die with an exception
                # in multiprocessing.util:258
                #log.exception("Failed to delete temporary file %s", target)
                pass
            del self.vault[path]
        else:
            if not os.path.exists(path):
                raise OSError(errno.ENOENT,
                        "[Errno 2] No such file or directory: '%s'" % path)
            self.vault[path] = dict(tempfile=path, deleted=True)

    def tpc_begin(self, transaction):
        pass

    def commit(self, transaction):
        self.in_commit = True
        for target in self.vault:
            info = self.vault[target]
            if info.get("deleted", False):
                os.rename(target, "%s.filesafe" % target)
                info["has_original"] = True
                info["moved"] = True
            else:
                if os.path.exists(target):
                    info["has_original"] = True
                    os.link(target, "%s.filesafe" % target)
                else:
                    info["has_original"] = False
                rename = os.renames if info.get("recursive") else os.rename
                rename(info["tempfile"], target)
                info["moved"] = True

    def tpc_vote(self, transaction):
        pass

    def tpc_finish(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("deleted", False):
                try:
                    os.unlink("%s.filesafe" % info["tempfile"])
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to remove file backup for %s",
                    # target)
                    pass
            elif info.get("has_original"):
                try:
                    os.unlink("%s.filesafe" % target)
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to remove file backup for %s",
                    # target)
                    pass

        self.in_commit = False
        self._cleanup()

    def tpc_abort(self, transaction):
        for target in self.vault:
            info = self.vault[target]
            if info.get("moved"):
                try:
                    if info["has_original"]:
                        os.rename("%s.filesafe" % target, target)
                    elif 'source' in info:
                        rename = os.renames if info.get("recursive") else os.rename
                        rename(target, info["source"])
                    else:
                        os.unlink(target)
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to restore original file %s",
                    # target)
                    pass
            else:
                try:
                    os.unlink(info["tempfile"])
                except OSError:
                    # XXX log.exception makes the testruns die with an
                    # exception in multiprocessing.util:258
                    # log.exception("Failed to delete temporary file %s",
                    # target)
                    pass

        self.in_commit = False
        self._cleanup()

    abort = tpc_abort

    def sortKey(self):
        return "safety first"
