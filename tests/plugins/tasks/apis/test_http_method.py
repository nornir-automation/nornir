import json

from nornir.plugins.tasks.apis import http_method

import pytest

from requests.exceptions import HTTPError


BASE_URL = "http://httpbin"


class Test(object):
    def test_simple_get_text(self):
        url = "{}/encoding/utf8".format(BASE_URL)
        result = http_method(method="get", url=url)
        assert result.response.status_code
        assert result.result.startswith("<h1>Unicode Demo</h1>")
        assert result.result == result.response.text

    def test_simple_get_json(self):
        url = "{}/get".format(BASE_URL)
        result = http_method(method="get", url=url)
        assert result.response.status_code
        assert result.response.json()["args"] == {}
        assert json.loads(result.response.text)["args"] == {}
        assert result.result == result.response.json()

    def test_headers(self):
        url = "{}/headers".format(BASE_URL)
        headers = {"X-Test": "a test"}
        result = http_method(method="get", url=url, headers=headers)
        assert result.result["headers"]["X-Test"] == "a test"

    def test_params(self):
        url = "{}/get".format(BASE_URL)
        params = {"my_param": "my_value"}
        result = http_method(method="get", url=url, params=params)
        assert result.result["args"]["my_param"] == "my_value"

    def test_post_data(self):
        url = "{}/post".format(BASE_URL)
        data = {"my_param": "my_value"}
        result = http_method(method="post", url=url, data=data)
        assert result.result["form"]["my_param"] == "my_value"

    def test_post_json(self):
        url = "{}/post".format(BASE_URL)
        json = {"my_param": "my_value"}
        result = http_method(method="post", url=url, json=json)
        assert result.result["data"] == '{"my_param": "my_value"}'

    def test_raise_for_status(self):
        url = "{}/status/418".format(BASE_URL)

        with pytest.raises(HTTPError):
            http_method(method="post", url=url)

        result = http_method(method="post", url=url, raise_for_status=False)
        assert result.response.status_code

    def test_with_nornir(self, nornir):
        url = "{}/get".format(BASE_URL)
        params = {"my_param": "my_value"}

        r = nornir.run(http_method, method="get", url=url, params=params)

        processed = False
        for host, result in r.items():
            processed = True
            assert result[0].result["args"]["my_param"] == "my_value"
        assert processed
