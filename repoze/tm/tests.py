import unittest

class TestTM(unittest.TestCase):
    def _getTargetClass(self):
        from repoze.tm import TM
        return TM

    def _start_response(self, status, headers, exc_info=None):
        pass

    def _makeOne(self, app, commit_veto=None):
        return self._getTargetClass()(app, commit_veto)

    def test_ekey_inserted(self):
        app = DummyApplication()
        tm = self._makeOne(app)
        tm.transaction = DummyTransactionModule()
        from repoze.tm import ekey
        env = {}
        tm(env, self._start_response)
        self.failUnless(ekey in env)

    def test_committed(self):
        app = DummyApplication()
        tm = self._makeOne(app)
        transaction = DummyTransactionModule()
        tm.transaction = transaction
        result = tm({}, self._start_response)
        self.assertEqual(result, ['hello'])
        self.assertEqual(transaction.committed, True)
        self.assertEqual(transaction.aborted, False)

    def test_aborted_via_doom(self):
        app = DummyApplication()
        tm = self._makeOne(app)
        transaction = DummyTransactionModule(doom=True)
        tm.transaction = transaction
        result = tm({}, self._start_response)
        self.assertEqual(result, ['hello'])
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)

    def test_aborted_via_exception(self):
        app = DummyApplication(exception=True)
        tm = self._makeOne(app)
        transaction = DummyTransactionModule()
        tm.transaction = transaction
        self.assertRaises(ValueError, tm, {}, self._start_response)
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)
        
    def test_aborted_via_exception_and_doom(self):
        app = DummyApplication(exception=True)
        tm = self._makeOne(app)
        transaction = DummyTransactionModule(doom=True)
        tm.transaction = transaction
        self.assertRaises(ValueError, tm, {}, self._start_response)
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)

    def test_aborted_via_commit_veto(self):
        app = DummyApplication(status="403 Forbidden")
        def commit_veto(environ, status, headers):
            self.failUnless(isinstance(environ, dict),
                            "environ is not passed properly")
            self.failUnless(isinstance(headers, list),
                            "headers are not passed properly")
            self.failUnless(isinstance(status, str),
                            "status is not passed properly")
            return not (200 <= int(status.split()[0]) < 400)
        tm = self._makeOne(app, commit_veto)
        transaction = DummyTransactionModule()
        tm.transaction = transaction
        tm({}, self._start_response)
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)

    def test_committed_via_commit_veto_exception(self):
        app = DummyApplication(status="403 Forbidden")
        def commit_veto(environ, status, headers):
            return None
        tm = self._makeOne(app, commit_veto)
        transaction = DummyTransactionModule()
        tm.transaction = transaction
        tm({}, self._start_response)
        self.assertEqual(transaction.committed, True)
        self.assertEqual(transaction.aborted, False)

    def test_aborted_via_commit_veto_exception(self):
        app = DummyApplication(status="403 Forbidden")
        def commit_veto(environ, status, headers):
            raise ValueError('foo')
        tm = self._makeOne(app, commit_veto)
        transaction = DummyTransactionModule()
        tm.transaction = transaction
        self.assertRaises(ValueError, tm, {}, self._start_response)
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)

    def test_cleanup_on_commit(self):
        from repoze.tm import after_end
        dummycalled = []
        def dummy():
            dummycalled.append(True)
        env = {}
        app = DummyApplication()
        tm = self._makeOne(app)
        transaction = DummyTransactionModule()
        setattr(transaction, after_end.key, [dummy])
        tm.transaction = transaction
        tm(env, self._start_response)
        self.assertEqual(transaction.committed, True)
        self.assertEqual(transaction.aborted, False)
        self.assertEqual(dummycalled, [True])
        
    def test_cleanup_on_abort(self):
        from repoze.tm import after_end
        dummycalled = []
        def dummy():
            dummycalled.append(True)
        env = {}
        app = DummyApplication(exception=True)
        tm = self._makeOne(app)
        transaction = DummyTransactionModule()
        setattr(transaction, after_end.key, [dummy])
        tm.transaction = transaction
        self.assertRaises(ValueError, tm, env, self._start_response)
        self.assertEqual(transaction.committed, False)
        self.assertEqual(transaction.aborted, True)
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
        txn = Dummy()
        registry.register(func, txn)
        self.assertEqual(getattr(txn, registry.key), [func])

    def test_unregister_exists(self):
        registry = self._makeOne()
        func = lambda *x: None
        txn = Dummy()
        registry.register(func, txn)
        self.assertEqual(getattr(txn, registry.key), [func])
        registry.unregister(func, txn)
        self.failIf(hasattr(txn, registry.key))
        
    def test_unregister_notexists(self):
        registry = self._makeOne()
        func = lambda *x: None
        txn = Dummy()
        setattr(txn, registry.key, [None])
        registry.unregister(func, txn)
        self.assertEqual(getattr(txn, registry.key), [None])

    def test_unregister_funcs_is_None(self):
        registry = self._makeOne()
        func = lambda *x: None
        txn = Dummy()
        self.assertEqual(registry.unregister(func, txn), None)

class UtilityFunctionTests(unittest.TestCase):
    def test_isActive(self):
        from repoze.tm import ekey
        from repoze.tm import isActive
        self.assertEqual(isActive({ekey:True}), True)
        self.assertEqual(isActive({}), False)

class TestMakeTM(unittest.TestCase):
    def test_make_tm_withveto(self):
        from repoze.tm import make_tm
        tm = make_tm(DummyApplication(), {}, 'repoze.tm.tests:fakeveto')
        self.assertEqual(tm.commit_veto, fakeveto)

    def test_make_tm_noveto(self):
        from repoze.tm import make_tm
        tm = make_tm(DummyApplication(), {}, None)
        self.assertEqual(tm.commit_veto, None)

def fakeveto(environ, status, headers):
    pass

class DummyTransactionModule:
    begun = False
    committed = False
    aborted = False
    def __init__(self, doom=False):
        self.doom = doom

    def begin(self):
        self.begun = True

    def get(self):
        return self

    def commit(self):
        self.committed = True

    def abort(self):
        self.aborted = True

    def isDoomed(self):
        return self.doom

class Dummy:
    pass

class DummyApplication:
    def __init__(self, exception=False, status="200 OK"):
        self.exception = exception
        self.status = status
        
    def __call__(self, environ, start_response):
        start_response(self.status, [], None)
        if self.exception:
            raise ValueError('raising')
        return ['hello']

