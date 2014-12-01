from urllib import quote as urlquote
import urlparse

from pycache import Cache
from pycache.factory import NoCacheClientFactory, CacheClientFactory
from twisted.internet import reactor
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET


class CacheRouterResource(Resource):
    """
    Cache "router" that will read the cache-control header and attempt to send a response from cache.
    Currently supports: no-store, max-age
    """

    def __init__(self, host, port, path, cache=None, rct=reactor):
        Resource.__init__(self)
        self.host = host
        self.port = port
        self.path = path
        self.cache = cache or Cache()
        self.reactor = rct

    def getChild(self, path, request):
        # Get the cache-control header
        cache_control = request.getAllHeaders().get('cache-control', '')
        max_age = -1
        no_store = False
        # Read the comma delimited cache control values
        # We currently only support max-age and no-store.
        # Ex: max-age=86400, no-store (results in a no-store)
        for key in cache_control.split(','):
            if 'max-age' in key:
                # max-age format: max-age=<seconds>
                max_age_key = key.split('=')
                assert 2 >= len(max_age_key) > 1, 'max-age should be in the form max-age=<int>'
                # TODO: Can raise ValueError
                max_age = int(max_age_key[1])
            if 'no-store' in key:
                no_store = True
        # Do we want to use the cache?
        if max_age < 0 or no_store:
            return NoCacheResource(self.host, self.port, self.path + '/' + urlquote(path, safe=''),
                                   self.reactor)
        return CacheResource(
            self.host, self.port, self.path + '/' + urlquote(path, safe=''),
            max_age, self.cache, self.reactor)

    def render(self, request):
        """Should not be called. Render will be called on the resource returned by getChild"""
        raise NotImplementedError()


class BaseResource(Resource):
    def __init__(self, host, port, path, rct=reactor):
        Resource.__init__(self)
        self.host = host
        self.port = port
        self.path = path
        self.reactor = rct


class LeafResource(object):
    isLeaf = True

    def getChild(self, path, request):
        """Will not be called because this is a leaf"""
        raise NotImplementedError()


class CacheResource(BaseResource, LeafResource):
    """Attempts to read the request from cache. Otherwise, gets the response and caches it"""
    cacheClientFactoryClass = CacheClientFactory

    def __init__(self, host, port, path, max_age, cache=None, rct=reactor):
        BaseResource.__init__(self, host, port, path, rct)
        self.max_age = max_age
        self.cache = cache or Cache()

    def getChild(self, path, request):
        """Will not """
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


class NoCacheResource(BaseResource, LeafResource):
    """Will not attempt to retrieve request from cache nor cache the response"""
    cacheClientFactoryClass = NoCacheClientFactory

    def __init__(self, host, port, path, rct=reactor):
        BaseResource.__init__(self, host, port, path, rct)

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