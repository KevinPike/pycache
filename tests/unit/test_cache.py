from datetime import datetime
import unittest

from pycache.cache import Cache
from hamcrest import assert_that, is_


class TestCache(unittest.TestCase):
    def test_cache_put_get(self):
        cache = Cache()

        cache.put('/home', 'index')

        assert_that(cache.get('/home'), is_('index'))
        assert_that(cache.get('/away'), is_(None))

    def test_boundaries_has(self):
        cache = Cache()

        cache.put('/home', 'index', datetime(2014, 12, 12))

        current = datetime(2014, 12, 12, second=5)
        assert_that(cache.has('/home', 4, current), is_(False))
        assert_that(cache.has('/home', 5, current), is_(True))
        assert_that(cache.has('/home', 6, current), is_(True))