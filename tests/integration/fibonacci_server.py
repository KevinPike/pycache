from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import Site


def fib():
    yield 0
    a, b = 0, 1
    while True:
        a, b = b, a + b
        yield a


class FibonacciPage(Resource):
    """Simple fibonacci server for testing"""
    isLeaf = True

    def __init__(self):
        Resource.__init__(self)
        self.fib = fib()

    def render_GET(self, request):
        return '%s' % (self.fib.next(),)

    def render_POST(self, request):
        """Reset the server"""
        self.fib.close()
        self.fib = fib()
        return ''


if __name__ == '__main__':
    factory = Site(FibonacciPage())
    reactor.listenTCP(1123, factory)
    reactor.run()