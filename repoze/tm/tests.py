import unittest
import sys
import transaction

class TestTM(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.tm import TM
        return TM

    def _makeOne(self, app, endregistrations=None):
        from repoze.tm import after_end
        if endregistrations:
            after_end.register(*endregistrations)
        return self._getTargetClass()(app)

    def test_committed(self):
        resource = DummyResource()
        app = DummyApplication(resource)
        tm = self._makeOne(app)
        result = tm({}, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(resource.committed, True)
        self.assertEqual(resource.aborted, False)

    def test_aborted_via_doom(self):
        resource = DummyResource()
        app = DummyApplication(resource, doom=True)
        tm = self._makeOne(app)
        result = tm({}, None)
        self.assertEqual(result, ['hello'])
        self.assertEqual(transaction.isDoomed(), False)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)

    def test_aborted_via_exception(self):
        resource = DummyResource()
        app = DummyApplication(resource, exception=True)
        tm = self._makeOne(app)
        self.assertRaises(ValueError, tm, {}, None)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)
        
    def test_aborted_via_exception_and_doom(self):
        resource = DummyResource()
        app = DummyApplication(resource, exception=True, doom=True)
        tm = self._makeOne(app)
        self.assertRaises(ValueError, tm, {}, None)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)

    def test_cleanup_on_commit(self):
        dummycalled = []
        def dummy():
            dummycalled.append(True)
        env = {}
        resource = DummyResource()
        app = DummyApplication(resource, exception=False, doom=False)
        tm = self._makeOne(app, (dummy, env))
        tm(env, None)
        self.assertEqual(resource.committed, True)
        self.assertEqual(resource.aborted, False)
        self.assertEqual(dummycalled, [True])
        
    def test_cleanup_on_abort(self):
        dummycalled = []
        def dummy():
            dummycalled.append(True)
        env = {}
        resource = DummyResource()
        app = DummyApplication(resource, exception=True, doom=False)
        tm = self._makeOne(app, (dummy, env))
        self.assertRaises(ValueError, tm, env, None)
        self.assertEqual(resource.committed, False)
        self.assertEqual(resource.aborted, True)
        self.assertEqual(dummycalled, [True])

class TestAfterEnd(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.tm import AfterEnd
        return AfterEnd

    def _makeOne(self):
        return self._getTargetClass()()

    def test_register(self):
        registry = self._makeOne()
        func = lambda *x: None
        environ = {}
        registry.register(func, environ)
        self.assertEqual(environ[registry.key], [func])

    def test_unregister_exists(self):
        registry = self._makeOne()
        func = lambda *x: None
        environ = {}
        registry.register(func, environ)
        registry.unregister(func, environ)
        self.assertEqual(environ[registry.key], [])
        
    def test_unregister_notexists(self):
        registry = self._makeOne()
        func = lambda *x: None
        environ = {registry.key:[None]}
        registry.unregister(func, environ)
        self.assertEqual(environ[registry.key], [None])

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
