from pycache.client import BaseClient, CacheClient
from twisted.internet.protocol import ClientFactory


class BaseFactory(ClientFactory):
    def __init__(self, command, rest, version, headers, data, response):
        self.response = response
        self.command = command
        self.rest = rest
        self.headers = headers
        self.data = data
        self.version = version

    def clientConnectionFailed(self, connector, reason):
        self.response.setResponseCode(501, "Gateway error")
        self.response.responseHeaders.addRawHeader("Content-Type", "text/html")
        self.response.write("<H1>Could not connect</H1>")
        self.response.finish()


class NoCacheClientFactory(BaseFactory):
    protocol = BaseClient

    def __init__(self, command, rest, version, headers, data, response):
        BaseFactory.__init__(self, command, rest, version, headers, data, response)

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.rest, self.version,
                             self.headers, self.data, self.response)


class CacheClientFactory(BaseFactory):
    protocol = CacheClient

    def __init__(self, command, rest, version, headers, data, response, cache):
        self.cache = cache
        BaseFactory.__init__(self, command, rest, version, headers, data, response)

    def buildProtocol(self, addr):
        return self.protocol(self.command, self.rest, self.version,
                             self.headers, self.data, self.response, self.cache)
