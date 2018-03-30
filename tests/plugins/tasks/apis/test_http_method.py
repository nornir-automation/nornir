import json

from brigade.plugins.tasks.apis import http_method

import pytest

from requests.exceptions import HTTPError


class Test(object):

    def test_simple_get_text(self):
        url = "http://httpbin.org/encoding/utf8"
        result = http_method(method="get", url=url)
        assert result.response.status_code
        assert result.result.startswith("<h1>Unicode Demo</h1>")
        assert result.result == result.response.text

    def test_simple_get_json(self):
        url = "http://httpbin.org/get"
        result = http_method(method="get", url=url)
        assert result.response.status_code
        assert result.response.json()["args"] == {}
        assert json.loads(result.response.text)["args"] == {}
        assert result.result == result.response.json()

    def test_headers(self):
        url = "http://httpbin.org/headers"
        headers = {"X-Test": "a test"}
        result = http_method(method="get", url=url, headers=headers)
        assert result.result["headers"]["X-Test"] == "a test"

    def test_params(self):
        url = "http://httpbin.org/get"
        params = {"my_param": "my_value"}
        result = http_method(method="get", url=url, params=params)
        assert result.result["args"]["my_param"] == "my_value"

    def test_post_data(self):
        url = "http://httpbin.org/post"
        data = {"my_param": "my_value"}
        result = http_method(method="post", url=url, data=data)
        assert result.result["form"]["my_param"] == "my_value"

    def test_post_json(self):
        url = "http://httpbin.org/post"
        json = {"my_param": "my_value"}
        result = http_method(method="post", url=url, json=json)
        assert result.result["data"] == '{"my_param": "my_value"}'

    def test_raise_for_status(self):
        url = "http://httpbin.org/status/418"

        with pytest.raises(HTTPError):
            http_method(method="post", url=url)

        result = http_method(method="post", url=url, raise_for_status=False)
        assert result.response.status_code
