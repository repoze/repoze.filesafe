# repoze TransactionManager WSGI middleware
import transaction
import threading
from repoze.filesafe.manager import FileSafeDataManager

_local = threading.local()


def createFile(path, mode="w"):
    vault = getattr(_local, "vault", None)
    if vault is None:
        raise RuntimeError("No FileSafeDataManager found")
    return vault.createFile(path, mode)


def openFile(path, mode="r"):
    vault = getattr(_local, "vault", None)
    if vault is None:
        raise RuntimeError("No FileSafeDataManager found")
    return vault.openFile(path, mode)


def deleteFile(path):
    vault = getattr(_local, "vault", None)
    if vault is None:
        raise RuntimeError("No FileSafeDataManager found")
    return vault.deleteFile(path)


class FileSafeMiddleware(object):
    def __init__(self, app, config=None, **kwargs):
        self.app = app

    def __call__(self, environ, start_response):
        if not hasattr(_local, "vault"):
            _local.vault = FileSafeDataManager()
        tx = transaction.get()
        tx.join(_local.vault)
        return self.app(environ, start_response)


def filesafe_filter_factory(global_conf, **kwargs):
    def filter(app):
        return FileSafeMiddleware(app, global_conf, **kwargs)
    return filter


def filesafe_filter_app_factory(app, global_conf, **kwargs):
    return FileSafeMiddleware(app, global_conf, **kwargs)
