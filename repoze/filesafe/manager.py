import logging
import os.path
import tempfile
from zope.interface import implements
from transaction.interfaces import IDataManager

log = logging.getLogger("repoze.filesafe")


class FileSafeDataManager:
    implements(IDataManager)

    transaction_manager = None

    def __init__(self, tempdir=None):
        self.tempdir=tempdir
        self.in_commit=False
        self.vault={}


    def createFile(self, path, mode):
        if path in self.vault:
            raise ValueError("%s is already taken", path)
        file=tempfile.NamedTemporaryFile(mode=mode, dir=self.tempdir,
                delete=False)
        self.vault[path]=dict(tempfile=file.name)
        return file


    def tpc_begin(self, transaction):
        pass



    def commit(self, transaction):
        self.in_commit=True
        for target in self.vault:
            info=self.vault[target]
            if os.path.exists(target):
                info["has_original"]=True
                os.link(target, "%s.filesafe" % target)
            else:
                info["has_original"]=False
            os.rename(info["tempfile"], target)
            info["moved"]=True


    def tpc_vote(self, transaction):
        pass


    def tpc_finish(self, transaction):
        for target in self.vault:
            info=self.vault[target]
            if info.get("has_original"):
                try:
                    os.unlink("%s.filesafe" % target)
                except OSError:
                    # XXX log.exception makes the testruns die with an exception
                    # in multiprocessing.util:258
                    #log.exception("Failed to remove file backup for %s", target)
                    pass

        self.vault.clear()
        self.in_commit=False


    def tpc_abort(self, transaction):
        for target in self.vault:
            info=self.vault[target]
            if info.get("moved"):
                try:
                    if info["has_original"]:
                        os.rename("%s.filesafe" % target, target)
                    else:
                        os.unlink(target)
                except OSError:
                    # XXX log.exception makes the testruns die with an exception
                    # in multiprocessing.util:258
                    #log.exception("Failed to restore original file %s", target)
                    pass
            else:
                try:
                    os.unlink(info["tempfile"])
                except OSError:
                    # XXX log.exception makes the testruns die with an exception
                    # in multiprocessing.util:258
                    #log.exception("Failed to delete temporary file %s", target)
                    pass

        self.vault.clear()
        self.in_commit=False

    abort = tpc_abort


    def sortKey(self):
        return "safety first"

