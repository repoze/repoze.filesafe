# repoze TransactionManager WSGI middleware
import transaction

class TM:
    def __init__(self, application):
        self.application = application
        
    def __call__(self, environ, start_response):
        transaction.begin()
        try:
            result = self.application(environ, start_response)
        except:
            self.abort(environ)
            raise
        else:
            if transaction.isDoomed():
                self.abort(environ)
            else:
                self.commit(environ)
        return result

    def commit(self, environ):
        transaction.commit()
        after_end.cleanup(environ)

    def abort(self, environ):
        transaction.abort()
        after_end.cleanup(environ)

# Callback registry API helper class
class AfterEnd:
    key = 'repoze.tm.afterend'
    def register(self, func, environ):
        cleanup = environ.setdefault(self.key, [])
        cleanup.append(func)

    def unregister(self, func, environ):
        cleanup = environ.get(self.key, [])
        new = []
        for f in cleanup:
            if f is func:
                continue
            new.append(f)
        environ[self.key] = new

    def cleanup(self, environ):
        for func in environ.setdefault(self.key, []):
            func()
        del environ[self.key]

# singleton, importable by other modules
after_end = AfterEnd()
    
def make_tm(app, global_conf):
    return TM(app)

