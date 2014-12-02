from pycache import CacheRouterResource, Cache

from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.web import server

import config

cache = Cache(config.timeout)
LoopingCall(cache.clean).start(config.interval)
site = server.Site(CacheRouterResource(config.host, config.port, '', cache))
reactor.listenTCP(config.server, site)
reactor.run()