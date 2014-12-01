from pycache.cache import CacheResponse
from twisted.web.http import HTTPClient


class BaseClient(HTTPClient):
    """Base for a reverse proxy client"""
    _finished = False

    def __init__(self, command, rest, version, headers, data, response):
        self.response = response
        self.command = command
        self.rest = rest
        if 'proxy-connection' in headers:
            del headers['proxy-connection']
        headers['connection'] = 'close'
        headers.pop('keep-alive', None)
        self.headers = headers
        self.data = data
        self.version = version

    def connectionMade(self):
        """Forwards request to external server"""
        self.sendCommand(self.command, self.rest)
        for header, value in self.headers.items():
            self.sendHeader(header, value)
        self.endHeaders()
        self.transport.write(self.data)

    def handleStatus(self, version, code, message):
        self.response.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        if key.lower() in ['server', 'date', 'content-type']:
            self.response.responseHeaders.setRawHeaders(key, [value])
        else:
            self.response.responseHeaders.addRawHeader(key, value)

    def handleResponsePart(self, buffer):
        """Writes response body to client"""
        self.response.write(buffer)

    def handleResponseEnd(self):
        if not self._finished:
            self._finished = True
            self.response.finish()
            self.transport.loseConnection()


class CacheClient(BaseClient):
    """Puts response request in cache"""
    def __init__(self, command, rest, version, headers, data, response, cache):
        BaseClient.__init__(self, command, rest, version, headers, data, response)
        self.response_body = ''
        self.cache = cache

    def handleResponsePart(self, buffer):
        self.response_body += buffer
        BaseClient.handleResponsePart(self, buffer)

    def handleResponseEnd(self):
        if not self._finished:
            self.cache.put(self.rest, CacheResponse(self.response, self.response_body))
            BaseClient.handleResponseEnd(self)