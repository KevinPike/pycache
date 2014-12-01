from datetime import datetime
import urlparse
from urllib import quote as urlquote

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory
from twisted.web.http import HTTPClient
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET


class CacheResponse(object):
    headers = ['server', 'date', 'content-type', 'content-length']

    def __init__(self, father, response_body):
        self.code = father.code
        self.message = father.code_message
        self.responseHeaders = father.responseHeaders
        self.response_body = response_body

    def update(self, request):
        request.setResponseCode(int(self.code), self.message)
        # Set headers
        for header in self.headers:
            request.responseHeaders.setRawHeaders(header, self.responseHeaders.getRawHeaders(header))


class Cache(object):
    class Record(object):
        def __init__(self, data, timestamp=None):
            self.data = data
            self.timestamp = timestamp or datetime.utcnow()

    def __init__(self):
        self.cache = {}

    def put(self, path, data, timestamp=None):
        self.cache[path] = Cache.Record(data, timestamp)

    def has(self, path, age, current_time=None):
        current_time = current_time or datetime.utcnow()
        if path not in self.cache:
            return False

        record = self.cache[path]
        return age >= (current_time - record.timestamp).total_seconds()

    def get(self, path):
        record = self.cache.get(path)
        if record:
            return record.data

        return None


class BaseClient(HTTPClient):
    _finished = False

    def __init__(self, command, rest, version, headers, data, father):
        self.father = father
        self.command = command
        self.rest = rest
        if "proxy-connection" in headers:
            del headers["proxy-connection"]
        headers["connection"] = "close"
        headers.pop('keep-alive', None)
        self.headers = headers
        self.data = data
        self.version = version

    # Send request to server
    def connectionMade(self):
        self.sendCommand(self.command, self.rest)
        for header, value in self.headers.items():
            self.sendHeader(header, value)
        self.endHeaders()
        self.transport.write(self.data)

    def handleStatus(self, version, code, message):
        self.father.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        if key.lower() in ['server', 'date', 'content-type']:
            self.father.responseHeaders.setRawHeaders(key, [value])
        else:
            self.father.responseHeaders.addRawHeader(key, value)

    def handleResponsePart(self, buffer):
        self.father.write(buffer)

    def handleResponseEnd(self):
        """
        Finish the original request, indicating that the response has been
        completely written to it, and disconnect the outgoing transport.
        """
        if not self._finished:
            self._finished = True
            self.father.finish()
            self.transport.loseConnection()


class CacheClient(BaseClient):
    def __init__(self, command, rest, version, headers, data, father, cache):
        BaseClient.__init__(self, command, rest, version, headers, data, father)
        self.response_body = ""
        self.cache = cache

    def handleResponsePart(self, buffer):
        self.response_body += buffer
        BaseClient.handleResponsePart(self, buffer)

    def handleResponseEnd(self):
        if not self._finished:
            self.cache.put(self.rest, CacheResponse(self.father, self.response_body))
            BaseClient.handleResponseEnd(self)


class BaseFactory(ClientFactory):
    def __init__(self, command, rest, version, headers, data, father):
        self.father = father
        self.command = command
        self.rest = rest
        self.headers = headers
        self.data = data
        self.version = version

    def clientConnectionFailed(self, connector, reason):
        """
        Report a connection failure in a response to the incoming request as
        an error.
        """
        self.father.setResponseCode(501, "Gateway error")
        self.father.responseHeaders.addRawHeader("Content-Type", "text/html")
        self.father.write("<H1>Could not connect</H1>")
        self.father.finish()


class NoCacheClientFactory(BaseFactory):
    protocol = BaseClient

    def __init__(self, command, rest, version, headers, data, father):
        BaseFactory.__init__(self, command, rest, version, headers, data, father)

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.rest, self.version,
                             self.headers, self.data, self.father)


class CacheClientFactory(BaseFactory):
    protocol = CacheClient

    def __init__(self, command, rest, version, headers, data, father, cache):
        self.cache = cache
        BaseFactory.__init__(self, command, rest, version, headers, data, father)

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.rest, self.version,
                             self.headers, self.data, self.father, self.cache)


class CacheRouterResource(Resource):
    def __init__(self, host, port, path, cache=None, reactor=reactor):
        Resource.__init__(self)
        self.host = host
        self.port = port
        self.path = path
        self.cache = cache or Cache()
        self.reactor = reactor

    def getChild(self, path, request):
        """
        Create and return a proxy resource with the same proxy configuration
        as this one, except that its path also contains the segment given by
        C{path} at the end.
        """
        # Check if request headers for cache
        cache_control = request.getAllHeaders().get('cache-control', "")
        # If no cache headers, return a Resource that will render the url
        # If cache headers, see if item is in cache
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
        # If in cache, return a Resource that renders from cache
        # Else, return a Resource that will save the response to cache
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