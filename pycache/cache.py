from datetime import datetime


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