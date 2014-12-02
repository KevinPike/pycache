from datetime import datetime, timedelta
import unittest

from pycache.cache import Cache
from hamcrest import assert_that, is_, has_length


class TestCache(unittest.TestCase):
    def test_cache_put_get(self):
        cache = Cache(180000)

        cache.put('/home', 'index')

        assert_that(cache.get('/home'), is_('index'))
        assert_that(cache.get('/away'), is_(None))

    def test_boundaries_has(self):
        cache = Cache(18000)

        cache.put('/home', 'index', datetime(2014, 12, 12))

        current = datetime(2014, 12, 12, second=5)
        assert_that(cache.has('/home', 4, current), is_(False))
        assert_that(cache.has('/home', 5, current), is_(True))
        assert_that(cache.has('/home', 6, current), is_(True))

    def test_clean(self):
        cache = Cache(5)

        time = datetime(2014, 12, 12)

        cache.put('/home', 'index', time)
        cache.put('/next', 'before', time + timedelta(0, 1))

        cache.clean(time + timedelta(0, 4))
        assert_that(cache.cache, has_length(2))

        cache.clean(time + timedelta(0, 6))
        assert_that(cache.cache, has_length(1))

        cache.clean(time + timedelta(0, 7))
        assert_that(cache.cache, has_length(0))
