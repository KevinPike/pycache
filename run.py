from pycache import CacheRouterResource, Cache

from twisted.internet import reactor
from twisted.web import server

import config


site = server.Site(CacheRouterResource(config.host, config.port, '', Cache()))
reactor.listenTCP(config.server, site)
reactor.run()