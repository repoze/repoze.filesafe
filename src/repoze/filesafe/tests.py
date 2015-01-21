import errno
import os
import shutil
import tempfile
import unittest
from repoze.filesafe.manager import FileSafeDataManager
from repoze.filesafe.testing import DummyDataManager
from repoze.filesafe.testing import MockBytesIO
from repoze.filesafe.testing import MockStringIO


class Test_get_manager(unittest.TestCase):

    def tearDown(self):
        from repoze.filesafe import _remove_manager
        _remove_manager()

    def _callFUT(self, *a, **kw):
        from repoze.filesafe import _get_manager
        return _get_manager(*a, **kw)

    def test_full_cycle(self):
        import transaction
        from repoze.filesafe import _local
        self.assertTrue(not hasattr(_local, 'manager'))
        mgr = self._callFUT()
        self.assertTrue(isinstance(mgr, FileSafeDataManager))
        self.assertTrue(_local.manager is mgr)
        transaction.get().abort()
        self.assertTrue(not hasattr(_local, 'manager'))


class Test_create_file(unittest.TestCase):

    def tearDown(self):
        from repoze.filesafe import _remove_manager
        _remove_manager()

    def _callFUT(self, *a, **kw):
        from repoze.filesafe import create_file
        return create_file(*a, **kw)

    def test_custom_tempdir_create_file(self):
        test_tempdir = tempfile.mkdtemp()
        try:
            newfile = self._callFUT("tst", "w", test_tempdir)
            self.assertEqual(os.path.dirname(newfile.name), test_tempdir)
            self.failUnless(callable(newfile.read))
            self.failUnless(callable(newfile.write))
        finally:
            shutil.rmtree(test_tempdir)


class FileSafeDataManagerTests(unittest.TestCase):
    DM = FileSafeDataManager

    def exists(self, path):
        return os.path.exists(path)

    def open(self, path, mode=None):
        if mode is None:
            return open(path)
        else:
            return open(path, mode)

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.dm = self.DM(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_create_file(self):
        dm = self.dm
        newfile = dm.create_file("tst", "w")
        self.assertEqual(list(dm.vault.keys()), ["tst"])
        self.failUnless(callable(newfile.read))
        self.failUnless(callable(newfile.write))

    def test_can_not_create_file_twice(self):
        dm = self.dm
        dm.create_file("tst", "w")
        self.assertRaises(ValueError, dm.create_file, "tst", "w")

    def test_create_text_file(self):
        dm = self.dm
        newfile = dm.create_file('tst', 'w')
        newfile.write('Hello')

    def test_create_bytesfile(self):
        dm = self.dm
        newfile = dm.create_file('tst', 'wb')
        newfile.write(b'Hello')

    def test_commit_without_original(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        newfile = dm.create_file(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], False)
        self.assertEqual(self.exists(dm.vault[target]["tempfile"]), False)
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "Hello, World!")

    def test_commit_with_original(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        oldfile = self.open(target, "w")
        oldfile.write("...---...")
        oldfile.close()
        newfile = dm.create_file(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], True)
        self.assertEqual(self.open(target).read(), "Hello, World!")
        self.assertEqual(self.exists("%s.filesafe" % target), True)

    def test_finish_without_originals(self):
        dm = self.dm
        dm.vault = dict(one={}, two={})
        dm.tpc_finish(None)
        self.assertEqual(dm.vault, {})
        self.assertEqual(dm.in_commit, False)

    def test_finish_with_original(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open("%s.filesafe" % target, "w").close()
        dm.vault = {target: dict(has_original=True)}
        dm.tpc_finish(None)
        self.assertEqual(self.exists("%s.filesafe" % target), False)

    def test_finish_with_missing_original(self):
        dm = self.dm
        # Corner case: original was removed by someone else
        target = os.path.join(self.tempdir, "greeting")
        dm.vault = {target: dict(has_original=True)}
        dm.tpc_finish(None)

    def test_abort_with_moved_file(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        dm.vault = {target: dict(has_original=False, moved=True)}
        dm.tpc_abort(None)
        self.assertEqual(self.exists(target), False)

    def test_abort_with_moved_file_with_original(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        targetsafe = target + ".filesafe"
        f = self.open(targetsafe, "w")
        f.write("...---...")
        f.close()
        dm.vault = {target: dict(has_original=True, moved=True)}
        dm.tpc_abort(None)
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.exists(targetsafe), False)
        self.assertEqual(self.open(target).read(), "...---...")

    def test_abort_with_unmoved_file(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        dm.vault = {"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)
        self.assertEqual(self.exists(target), False)

    def test_abort_with_unmoved_file_which_disappeared(self):
        dm = self.dm
        # Corner case: temporary file disappeared
        target = os.path.join(self.tempdir, "greeting")
        dm.vault = {"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)

    def test_open_file_in_vault(self):
        dm = self.dm
        f = dm.create_file("dummy", "w")
        f.write("Hello!")
        f.close()
        f = dm.open_file("dummy")
        self.assertEqual(f.read(), "Hello!")
        f.close()

    def test_open_file_outside_vault(self):
        dm = self.dm
        f = dm.open_file(__file__)
        self.failUnless("testOpenFileInVault" in f.read())
        f.close()

    def test_delete_new_file_before_commit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.create_file(target, "w")
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        self.assertRaises(IOError, dm.open_file, target, "r")

    def test_delete_existing_file_before_commit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        # the file isn't actually gone, but can't be opened anymore
        self.assertRaises(IOError, dm.open_file, target, "r")
        self.assertEqual(self.exists(target), True)

    def test_delete_new_file_before_abort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.create_file(target, "w")
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        dm.commit(None)
        dm.tpc_abort(None)
        self.assertRaises(IOError, dm.open_file, target, "r")
        self.assertEqual(self.exists(target), False)

    def test_delete_existing_file_before_abort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        dm.commit(None)
        dm.tpc_abort(None)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)

    def test_delete_new_file_before_finish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.create_file(target, "w")
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        dm.commit(None)
        dm.tpc_finish(None)
        self.assertRaises(IOError, dm.open_file, target, "r")
        self.assertEqual(self.exists(target), False)

    def test_delete_existing_file_before_finish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        dm.commit(None)
        dm.tpc_finish(None)
        self.assertRaises(IOError, dm.open_file, target, "r")
        self.assertEqual(self.exists(target), False)

    def test_delete_and_recreate_new_file_before_commit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        created_file = dm.create_file(target, "w")
        created_file.write("a")
        created_file.close()
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        recreated_file = dm.create_file(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        newfile = dm.open_file(target, "r")
        self.assertEqual(newfile.read(), "b")

    def test_delete_and_recreate_existing_file_before_commit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        recreated_file = dm.create_file(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        newfile = dm.open_file(target, "r")
        self.assertEqual(newfile.read(), "b")
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "a")

    def test_delete_and_recreate_existing_file_before_abort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        recreated_file = dm.create_file(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_abort(None)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "a")

    def test_delete_and_recreate_new_file_before_finish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.create_file(target, "w")
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        recreated_file = dm.create_file(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_finish(None)
        newfile = dm.open_file(target, "r")
        self.assertEqual(newfile.read(), "b")
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "b")

    def test_delete_and_recreate_existing_file_before_finish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.delete_file(target)
        recreated_file = dm.create_file(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_finish(None)
        newfile = dm.open_file(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "b")

    def test_delete_non_existing_file(self):
        dm = self.dm
        try:
            dm.delete_file('/non-existing-file')
        except OSError as e:
            assert e.errno == errno.ENOENT
        else:
            self.fail('No OSError exception raised')


class FileSafeRenameFileTests(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.dm = FileSafeDataManager(self.tempdir)

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_rename_file(self):
        dm = self.dm
        source = os.path.join(self.tempdir, "foo")
        target = os.path.join(self.tempdir, "bar")
        with open(source, "w") as fd:
            fd.write("...---...")
        self.assertEqual(os.path.exists(source), True)
        self.assertEqual(os.path.exists(target), False)
        dm.rename_file(source, target)
        dm.commit(None)
        dm.tpc_finish(None)
        newfile = dm.open_file(target, "r")
        self.assertEqual(newfile.read(), "...---...")
        self.assertEqual(os.path.exists(target), True)
        self.assertEqual(open(target).read(), "...---...")
        self.assertEqual(os.path.exists(source), False)

    def test_abort_rename_file(self):
        dm = self.dm
        source = os.path.join(self.tempdir, "foo")
        target = os.path.join(self.tempdir, "bar")
        with open(source, "w") as fd:
            fd.write("...---...")
        self.assertEqual(os.path.exists(source), True)
        self.assertEqual(os.path.exists(target), False)
        dm.rename_file(source, target)
        dm.commit(None)
        dm.tpc_abort(None)
        self.assertEqual(os.path.exists(target), False)
        self.assertEqual(os.path.exists(source), True)
        self.assertEqual(open(source).read(), "...---...")


class DummyDataManagerTests(FileSafeDataManagerTests):
    DM = DummyDataManager

    def exists(self, path):
        return path in self.dm.data

    def open(self, path, mode='r'):
        cls = MockBytesIO if 'b' in mode else MockStringIO
        if mode is None or 'r' in mode:
            return cls(self.dm.data[path].mockdata)
        elif 'w' in mode:
            f = self.dm.data[path] = cls()
            return f

    def setUp(self):
        self.tempdir = "/dummy"
        self.dm = self.DM(self.tempdir)

    def tearDown(self):
        pass

    def test_delete_non_existing_file(self):
        pass
