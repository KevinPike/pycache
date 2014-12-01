from urllib import quote as urlquote
import urlparse

from pycache import Cache
from pycache.factory import NoCacheClientFactory, CacheClientFactory
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET


class CacheRouterResource(Resource):
    def __init__(self, host, port, path, cache=None, rct=reactor):
        Resource.__init__(self)
        self.host = host
        self.port = port
        self.path = path
        self.cache = cache or Cache()
        self.reactor = rct

    def getChild(self, path, request):
        cache_control = request.getAllHeaders().get('cache-control', "")
        max_age = -1
        no_store = False
        cache_controls = cache_control.split(',')
        for key in cache_controls:
            if 'max-age' in key:
                max_age_key = key.split('=')
                assert 2 >= len(max_age_key) > 1, "Invalid cache-control max-age"
                try:
                    max_age = int(max_age_key[1])
                except ValueError:
                    pass
            if 'no-store' in key:
                no_store = True
        if max_age < 0 or no_store:
            return NoCacheResource(self.host, self.port, self.path + '/' + urlquote(path, safe=""),
                                   self.reactor)

        return CacheResource(
            self.host, self.port, self.path + '/' + urlquote(path, safe=""),
            max_age, self.cache, self.reactor)

    def render(self, request):
        raise NotImplementedError()


class BaseResource(Resource):
    def __init__(self, host, port, path, rct=reactor):
        Resource.__init__(self)
        self.host = host
        self.port = port
        self.path = path
        self.reactor = rct


class CacheResource(BaseResource):
    cacheClientFactoryClass = CacheClientFactory

    def __init__(self, host, port, path, max_age, cache=None, rct=reactor):
        BaseResource.__init__(self, host, port, path, rct)
        self.max_age = max_age
        self.cache = cache or Cache()

    def getChild(self, path, request):
        raise NotImplementedError()

    def render(self, request):
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path
        if self.cache.has(rest, self.max_age):
            cache_response = self.cache.get(rest)
            cache_response.update(request)
            return cache_response.response_body
        else:
            clientFactory = self.cacheClientFactoryClass(
                request.method, rest, request.clientproto,
                request.getAllHeaders(), request.content.read(), request, self.cache)
            self.reactor.connectTCP(self.host, self.port, clientFactory)
            return NOT_DONE_YET


class NoCacheResource(BaseResource):
    cacheClientFactoryClass = NoCacheClientFactory

    def __init__(self, host, port, path, rct=reactor):
        BaseResource.__init__(self, host, port, path, rct)

    def getChild(self, path, request):
        raise NotImplementedError()

    def render(self, request):
        request.content.seek(0, 0)
        qs = urlparse.urlparse(request.uri)[4]
        if qs:
            rest = self.path + '?' + qs
        else:
            rest = self.path
        clientFactory = self.cacheClientFactoryClass(
            request.method, rest, request.clientproto,
            request.getAllHeaders(), request.content.read(), request)
        self.reactor.connectTCP(self.host, self.port, clientFactory)
        return NOT_DONE_YET