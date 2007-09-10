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
        self.cleanup(environ)

    def abort(self, environ):
        transaction.abort()
        self.cleanup(environ)

    def cleanup(self, environ):
        cleanup = environ.get('tm.cleanup', None)
        if cleanup is not None:
            cleanup.clear()

def make_tm(app, global_conf):
    return TM(app)
