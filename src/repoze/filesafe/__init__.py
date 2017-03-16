# repoze TransactionManager WSGI middleware
import threading
import warnings
import transaction
from repoze.filesafe.manager import FileSafeDataManager

_local = threading.local()


def _remove_manager(*a):
    try:
        del _local.manager
    except AttributeError:
        pass

def _get_manager(tempdir=None):
    manager = getattr(_local, 'manager', None)
    if manager is not None:
        return manager

    manager = _local.manager = FileSafeDataManager(tempdir)
    tx = transaction.get()
    tx.join(manager)
    tx.addAfterCommitHook(_remove_manager)
    return manager


def create_file(path, mode='w', tempdir=None):
    mgr = _get_manager(tempdir)
    return mgr.create_file(path, mode)


def rename_file(src, dst, recursive=False):
    mgr = _get_manager()
    return mgr.rename_file(src, dst, recursive)


def open_file(path, mode='r'):
    mgr = _get_manager()
    return mgr.open_file(path, mode)


def delete_file(path):
    mgr = _get_manager()
    return mgr.delete_file(path)


def file_exists(path):
    mgr = _get_manager()
    return mgr.file_exists(path)


class FileSafeMiddleware(object):
    def __init__(self, app, config=None, **kwargs):
        self.app = app
        warnings.warn('FileSafeMiddleware is no longer required. You can '
                      'safely remove it.',
                      DeprecationWarning, stacklevel=2)

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
