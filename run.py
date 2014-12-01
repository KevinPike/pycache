from pycache.cache import CacheRouterResource, Cache

from twisted.internet import reactor
from twisted.web import server

# Read host, port from config, server port

site = server.Site(CacheRouterResource('localhost', 8880, '', Cache()))
reactor.listenTCP(9090, site)
reactor.run()