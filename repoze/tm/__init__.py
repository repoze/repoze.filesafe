# repoze TransactionManager WSGI middleware
import transaction

ekey = 'repoze.tm.active'

class TM:
    def __init__(self, application, commit_veto=None):
        self.application = application
        self.commit_veto = commit_veto
        
    def __call__(self, environ, start_response):
        environ[ekey] = True
        transaction.begin()
        ctx = {}
        def save_status_and_headers(status, headers, exc_info=None):
            ctx.update(status=status, headers=headers)
            return start_response(status, headers, exc_info)
        try:
            result = self.application(environ, save_status_and_headers)
        except:
            self.abort()
            raise
        else:
            # ZODB 3.8 + has isDoomed
            if hasattr(transaction, 'isDoomed') and transaction.isDoomed():
                self.abort()
            if self.commit_veto is not None:
                try:
                    if self.commit_veto(environ, ctx['status'], ctx['headers']):
                        self.abort()
                except:
                    self.abort()
                    raise
                else:
                    self.commit()
            else:
                self.commit()
        return result

    def commit(self):
        t = transaction.get()
        t.commit()
        after_end.cleanup(t)

    def abort(self):
        t = transaction.get()
        t.abort()
        after_end.cleanup(t)

def isActive(environ):
    if ekey in environ:
        return True
    return False

# Callback registry API helper class
class AfterEnd:
    key = '_repoze_tm_afterend'
    def register(self, func, txn):
        funcs = getattr(txn, self.key, None)
        if funcs is None:
            funcs = []
            setattr(txn, self.key, funcs)
        funcs.append(func)

    def unregister(self, func, txn):
        funcs = getattr(txn, self.key, None)
        if funcs is None:
            return
        new = []
        for f in funcs:
            if f is func:
                continue
            new.append(f)
        if new:
            setattr(txn, self.key, new)
        else:
            delattr(txn, self.key)

    def cleanup(self, txn):
        funcs = getattr(txn, self.key, None)
        if funcs is not None:
            for func in funcs:
                func()
            delattr(txn, self.key)

# singleton, importable by other modules
after_end = AfterEnd()
    
def make_tm(app, global_conf):
    return TM(app)

