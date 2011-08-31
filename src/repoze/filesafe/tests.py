import os.path
import shutil
import tempfile
import unittest
from repoze.filesafe.manager import FileSafeDataManager
from repoze.filesafe.testing import DummyDataManager, MockFile


class _get_manager_tests(unittest.TestCase):
    def _get_manager(self, *a, **kw):
        from repoze.filesafe import _get_manager
        return _get_manager(*a, **kw)

    def test_full_cycle(self):
        import transaction
        from repoze.filesafe import _local
        self.assertTrue(not hasattr(_local, 'manager'))
        mgr = self._get_manager()
        self.assertTrue(isinstance(mgr, FileSafeDataManager))
        self.assertTrue(_local.manager is mgr)
        transaction.get().abort()
        self.assertTrue(not hasattr(_local, 'manager'))


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

    def testCreateFile(self):
        dm = self.dm
        newfile = dm.createFile("tst", "w")
        self.assertEqual(dm.vault.keys(), ["tst"])
        self.failUnless(callable(newfile.read))
        self.failUnless(callable(newfile.write))

    def testCanNotCreateFileTwice(self):
        dm = self.dm
        dm.createFile("tst", "w")
        self.assertRaises(ValueError, dm.createFile, "tst", "w")

    def testCommitWithoutOriginal(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        newfile = dm.createFile(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], False)
        self.assertEqual(self.exists(dm.vault[target]["tempfile"]), False)
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "Hello, World!")

    def testCommitWithOriginal(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        oldfile = self.open(target, "w")
        oldfile.write("...---...")
        oldfile.close()
        newfile = dm.createFile(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], True)
        self.assertEqual(self.open(target).read(), "Hello, World!")
        self.assertEqual(self.exists("%s.filesafe" % target), True)

    def testFinishWithoutOriginals(self):
        dm = self.dm
        dm.vault = dict(one={}, two={})
        dm.tpc_finish(None)
        self.assertEqual(dm.vault, {})
        self.assertEqual(dm.in_commit, False)

    def testFinishWithOriginal(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open("%s.filesafe" % target, "w").close()
        dm.vault = {target: dict(has_original=True)}
        dm.tpc_finish(None)
        self.assertEqual(self.exists("%s.filesafe" % target), False)

    def testFinishWithMissingOriginal(self):
        dm = self.dm
        # Corner case: original was removed by someone else
        target = os.path.join(self.tempdir, "greeting")
        dm.vault = {target: dict(has_original=True)}
        dm.tpc_finish(None)

    def testAbortWithMovedFile(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        dm.vault = {target: dict(has_original=False, moved=True)}
        dm.tpc_abort(None)
        self.assertEqual(self.exists(target), False)

    def testAbortWithMovedFileWithOriginal(self):
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

    def testAbortWithUnmovedFile(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        dm.vault = {"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)
        self.assertEqual(self.exists(target), False)

    def testAbortWithUnmovedFileWhichDisappeared(self):
        dm = self.dm
        # Corner case: temporary file disappeared
        target = os.path.join(self.tempdir, "greeting")
        dm.vault = {"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)

    def testOpenFileInVault(self):
        dm = self.dm
        f = dm.createFile("dummy", "w")
        f.write("Hello!")
        f.close()
        f = dm.openFile("dummy")
        self.assertEqual(f.read(), "Hello!")
        f.close()

    def testOpenFileOutsideVault(self):
        dm = self.dm
        f = dm.openFile(__file__)
        self.failUnless("testOpenFileInVault" in f.read())
        f.close()

    def testDeleteNewFileBeforeCommit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.createFile(target, "w")
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        self.assertRaises(IOError, dm.openFile, target, "r")

    def testDeleteExistingFileBeforeCommit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        # the file isn't actually gone, but can't be opened anymore
        self.assertRaises(IOError, dm.openFile, target, "r")
        self.assertEqual(self.exists(target), True)

    def testDeleteNewFileBeforeAbort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.createFile(target, "w")
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        dm.commit(None)
        dm.tpc_abort(None)
        self.assertRaises(IOError, dm.openFile, target, "r")
        self.assertEqual(self.exists(target), False)

    def testDeleteExistingFileBeforeAbort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        dm.commit(None)
        dm.tpc_abort(None)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)

    def testDeleteNewFileBeforeFinish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.createFile(target, "w")
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        dm.commit(None)
        dm.tpc_finish(None)
        self.assertRaises(IOError, dm.openFile, target, "r")
        self.assertEqual(self.exists(target), False)

    def testDeleteExistingFileBeforeFinish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        self.open(target, "w").close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        dm.commit(None)
        dm.tpc_finish(None)
        self.assertRaises(IOError, dm.openFile, target, "r")
        self.assertEqual(self.exists(target), False)

    def testDeleteAndRecreateNewFileBeforeCommit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        created_file = dm.createFile(target, "w")
        created_file.write("a")
        created_file.close()
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        recreated_file = dm.createFile(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        newfile = dm.openFile(target, "r")
        self.assertEqual(newfile.read(), "b")

    def testDeleteAndRecreateExistingFileBeforeCommit(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        recreated_file = dm.createFile(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        newfile = dm.openFile(target, "r")
        self.assertEqual(newfile.read(), "b")
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "a")

    def testDeleteAndRecreateExistingFileBeforeAbort(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        recreated_file = dm.createFile(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_abort(None)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "a")

    def testDeleteAndRecreateNewFileBeforeFinish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        dm.createFile(target, "w")
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        recreated_file = dm.createFile(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_finish(None)
        newfile = dm.openFile(target, "r")
        self.assertEqual(newfile.read(), "b")
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "b")

    def testDeleteAndRecreateExistingFileBeforeFinish(self):
        dm = self.dm
        target = os.path.join(self.tempdir, "greeting")
        existing_file = self.open(target, "w")
        existing_file.write("a")
        existing_file.close()
        self.assertEqual(self.exists(target), True)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        del newfile
        dm.deleteFile(target)
        recreated_file = dm.createFile(target, "w")
        recreated_file.write("b")
        recreated_file.close()
        dm.commit(None)
        dm.tpc_finish(None)
        newfile = dm.openFile(target, "r")
        self.failUnless(callable(newfile.read))
        self.assertEqual(self.exists(target), True)
        self.assertEqual(self.open(target).read(), "b")


class DummyDataManagerTests(FileSafeDataManagerTests):
    DM = DummyDataManager

    def exists(self, path):
        return path in self.dm.data

    def open(self, path, mode=None):
        if mode is None or 'r' in mode:
            return MockFile(self.dm.data[path].mockdata)
        elif 'w' in mode:
            f = self.dm.data[path] = MockFile()
            return f

    def setUp(self):
        self.tempdir = "/dummy"
        self.dm = self.DM(self.tempdir)

    def tearDown(self):
        pass
