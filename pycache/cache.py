from datetime import datetime


class CacheResponse(object):
    """Saves twisted request information so it can be used to update a request at a later time"""
    headers = ['server', 'date', 'content-type', 'content-length']

    def __init__(self, father, response_body):
        self.code = father.code
        self.message = father.code_message
        self.responseHeaders = father.responseHeaders
        self.response_body = response_body

    def update(self, request):
        request.setResponseCode(int(self.code), self.message)
        for header in self.headers:
            request.responseHeaders.setRawHeaders(header, self.responseHeaders.getRawHeaders(header))


# TODO: Thread safe?
class Cache(object):
    class Record(object):
        def __init__(self, data, timestamp=None):
            self.data = data
            self.timestamp = timestamp or datetime.utcnow()

    def __init__(self, expiration):
        """
        :param expiration: maximum age of record in cache, in seconds
        :return:
        """
        self.cache = {}
        self.expiration = expiration

    def put(self, path, data, timestamp=None):
        self.cache[path] = Cache.Record(data, timestamp)

    def has(self, path, age, current_time=None):
        """
        Checks to see if the cache has a path within a time range
        :param path: cache key
        :param age: maximum key age
        :param current_time: time for comparison
        :return: true if cache has path in age range; false otherwise
        """
        if path not in self.cache:
            return False

        current_time = current_time or datetime.utcnow()
        record = self.cache[path]
        # Compare age to time between current time and record creation timestamp
        return age >= (current_time - record.timestamp).total_seconds()

    def get(self, path):
        record = self.cache.get(path)
        return record.data if record else None

    def clean(self, current_time=None):
        """
        Removes all records that are older than expiration seconds
        :param current_time: injectable for testing, otherwise current time
        :return:
        """
        current_time = current_time or datetime.utcnow()
        keys_to_remove = []
        for key, record in self.cache.iteritems():
            if (current_time - record.timestamp).total_seconds() > self.expiration:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]