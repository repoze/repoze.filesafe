import unittest
import sys
import transaction

class TestTM(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.tm import TM
        return TM

    def _makeOne(self, *arg, **kw):
        return self._getTargetClass()(*arg, **kw)

    def test_committed(self):
        resource = DummyResource()
        app = DummyApplication(resource)
        tm = self._makeOne(app)
        cleanup = {1:1}
        result = tm({'tm.cleanup':cleanup}, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(resource.committed, True)
        self.assertEqual(resource.aborted, False)
        self.assertEqual(cleanup, {})

    def test_aborted_via_doom(self):
        resource = DummyResource()
        app = DummyApplication(resource, doom=True)
        tm = self._makeOne(app)
        cleanup = {1:1}
        result = tm({'tm.cleanup':cleanup}, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(transaction.isDoomed(), False)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)
        self.assertEqual(cleanup, {})

    def test_aborted_via_exception(self):
        resource = DummyResource()
        app = DummyApplication(resource, exception=True)
        tm = self._makeOne(app)
        cleanup = {1:1}
        self.assertRaises(ValueError, tm, {'tm.cleanup':cleanup}, None)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)
        self.assertEqual(cleanup, {})
        
    def test_aborted_via_exception_and_doom(self):
        resource = DummyResource()
        app = DummyApplication(resource, exception=True, doom=True)
        tm = self._makeOne(app)
        cleanup = {1:1}
        self.assertRaises(ValueError, tm, {'tm.cleanup':cleanup}, None)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)
        self.assertEqual(cleanup, {})

class DummyApplication:
    def __init__(self, resource, doom=False, exception=False):
        self.resource = resource
        self.doom = doom
        self.exception = exception
        
    def __call__(self, environ, start_response):
        transaction.get().join(self.resource)
        if self.doom:
            transaction.doom()
        if self.exception:
            raise ValueError('raising')
        return ['hello']

class DummyResource:
    committed = False
    aborted = False
    
    def sortKey(self):
        return 1

    tpc_finish = tpc_abort = tpc_vote = tpc_begin = lambda *arg: None

    def commit(self, txn):
        self.committed = True

    def abort(self, txn):
        self.aborted = True

def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
