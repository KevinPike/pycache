from pycache import CacheRouterResource, Cache
from tests.integration.fibonacci_server import FibonacciPage
from twisted.internet import reactor
from twisted.web.server import Site

# These ports should be OS chosen
reactor.listenTCP(1123, Site(FibonacciPage()))
reactor.listenTCP(9090, Site(CacheRouterResource('localhost', 1123, '', Cache())))
reactor.run()