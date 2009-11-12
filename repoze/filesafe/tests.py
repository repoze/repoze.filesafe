import os.path
import shutil
import tempfile
import unittest
from repoze.filesafe.manager import FileSafeDataManager

class FileSafeDataManagerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir=tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def testCreateFile(self):
        dm=FileSafeDataManager(self.tempdir)
        newfile=dm.createFile("tst", "w")
        self.assertEqual(dm.vault.keys(), ["tst"])
        self.failUnless(callable(newfile.read))
        self.failUnless(callable(newfile.write))

    def testCanNotCreateFileTwice(self):
        dm=FileSafeDataManager(self.tempdir)
        dm.createFile("tst", "w")
        self.assertRaises(ValueError, dm.createFile, "tst", "w")

    def testCommitWithoutOriginal(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        newfile=dm.createFile(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], False)
        self.assertEqual(os.path.exists(dm.vault[target]["tempfile"]), False)
        self.assertEqual(os.path.exists(target), True)
        self.assertEqual(open(target).read(), "Hello, World!")

    def testCommitWithOriginal(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        oldfile=open(target, "w")
        oldfile.write("...---...")
        oldfile.close()
        newfile=dm.createFile(target, "w")
        newfile.write("Hello, World!")
        newfile.close()
        dm.commit(None)
        self.assertEqual(dm.in_commit, True)
        self.assertEqual(dm.vault[target]["moved"], True)
        self.assertEqual(dm.vault[target]["has_original"], True)
        self.assertEqual(open(target).read(), "Hello, World!")
        self.assertEqual(os.path.exists("%s.filesafe" % target), True)

    def testFinishWithoutOriginals(self):
        dm=FileSafeDataManager(self.tempdir)
        dm.vault=dict(one={}, two={})
        dm.tpc_finish(None)
        self.assertEqual(dm.vault, {})
        self.assertEqual(dm.in_commit, False)

    def testFinishWithOriginal(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        open("%s.filesafe" % target, "w").close()
        dm.vault={target: dict(has_original=True)}
        dm.tpc_finish(None)
        self.assertEqual(os.path.exists("%s.filesafe" % target), False)

    def testFinishWithMissingOriginal(self):
        # Corner case: original was removed by someone else
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        dm.vault={target: dict(has_original=True)}
        dm.tpc_finish(None)

    def testAbortWithMovedFile(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        open(target, "w").close()
        dm.vault={target: dict(has_original=False, moved=True)}
        dm.tpc_abort(None)
        self.assertEqual(os.path.exists(target), False)

    def testAbortWithMovedFileWithOriginal(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        open(target, "w").close()
        targetsafe=target+".filesafe"
        f=open(targetsafe, "w")
        f.write("...---...")
        f.close()
        dm.vault={target: dict(has_original=True, moved=True)}
        dm.tpc_abort(None)
        self.assertEqual(os.path.exists(target), True)
        self.assertEqual(os.path.exists(targetsafe), False)
        self.assertEqual(open(target).read(), "...---...")

    def testAbortWithUnmovedFile(self):
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        open(target, "w").close()
        dm.vault={"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)
        self.assertEqual(os.path.exists(target), False)

    def testAbortWithUnmovedFileWhichDisappeared(self):
        # Corner case: temporary file disappeared
        dm=FileSafeDataManager(self.tempdir)
        target=os.path.join(self.tempdir, "greeting")
        dm.vault={"bogus": dict(moved=False, tempfile=target)}
        dm.tpc_abort(None)

    def testOpenFileInVault(self):
        dm=FileSafeDataManager(self.tempdir)
        f=dm.createFile("dummy", "w")
        f.write("Hello!")
        f.close()
        f=dm.openFile("dummy")
        self.assertEqual(f.read(), "Hello!")
        f.close()

    def testOpenFileOutsideVault(self):
        dm=FileSafeDataManager(self.tempdir)
        f=dm.openFile(__file__)
        self.failUnless("testOpenFileInVault" in f.read())
        f.close()



