from time import sleep
import unittest
import subprocess

import os

from hamcrest import assert_that, is_

from requests import request


current_directory = os.path.dirname(os.path.realpath(__file__))


class TestCacheRouter(unittest.TestCase):
    """Test running a external server and pointing the cache at it"""
    def setUp(self):
        self.p = subprocess.Popen(['python', "/".join([current_directory, 'run.py'])])
        self.external = 'http://localhost:1123/'
        self.cache = 'http://localhost:9090/'
        tries = 0
        while True:
            try:
                request('GET', self.external)
                break
            except Exception:
                tries += 1
                if tries > 10:
                    break
                sleep(.5)

        request('POST', self.external)

    def tearDown(self):
        self.p.terminate()

    # Make a couple requests, make sure we get the fib numbers we expected
    def test_no_store(self):
        fib = [0, 1, 1, 2, 3]

        for i in fib:
            response = request('GET', self.cache, headers={'cache-control': 'no-store'})
            assert_that(response.status_code, is_(200))

            assert_that(response.text, is_(str(i)))

    def test_max_age(self):
        response = request('GET', self.cache, headers={'cache-control': 'max-age=0'})
        assert_that(response.status_code, is_(200))
        assert_that(response.text, is_(str(0)))

        response = request('GET', self.cache, headers={'cache-control': 'max-age=5'})
        assert_that(response.status_code, is_(200))
        assert_that(response.text, is_(str(0)))

        response = request('GET', self.cache, headers={'cache-control': 'max-age=5'})
        assert_that(response.status_code, is_(200))
        assert_that(response.text, is_(str(0)))

        response = request('GET', self.cache, headers={'cache-control': 'max-age=0'})
        assert_that(response.status_code, is_(200))
        assert_that(response.text, is_(str(1)))

        for i in range(3):
            response = request('GET', self.cache, headers={'cache-control': 'max-age=10'})
            assert_that(response.status_code, is_(200))
            assert_that(response.text, is_(str(1)))

    def test_no_cache_control_headers(self):
        fib = [0, 1, 1, 2, 3]

        for i in fib:
            response = request('GET', self.cache)
            assert_that(response.status_code, is_(200))

            assert_that(response.text, is_(str(i)))