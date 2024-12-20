from functools import wraps
from logging import basicConfig, getLogger
from os import environ
from typing import Literal

import httpx
from dotenv import load_dotenv
from fire import Fire

load_dotenv()

TEST = "https://games-test.datsteam.dev/"
PROD = "https://games.datsteam.dev/"

KEY = environ["DAD_TOKEN"]


basicConfig(
    level="INFO",
    format="[%(levelname)s][%(name)s] %(message)s",
)

getLogger("httpx").setLevel("ERROR")


class DadAuth(httpx.Auth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
        # Send the request, with a custom `X-Authentication` header.
        request.headers["X-Auth-Token"] = self.token
        yield request


class ApiClient:
    def __init__(self, name: Literal["test", "prod"]):
        self.name = name
        self.base = PROD if name == "prod" else TEST
        logger_name = __name__ + "." + name
        self.logger = getLogger(logger_name)

        self._client = httpx.Client(
            auth=DadAuth(KEY),
            http1=True,
            http2=True,
            base_url=self.base,
        )

    @wraps(httpx.Client.request)
    def _request(self, method, url, **kwargs):
        """
        url without base - 'api/v1/games'
        httpx.request wrapper

        :return: response.json()
        """
        try:
            response = self._client.request(method, url, **kwargs)
        except Exception as e:
            self.logger.error(f"request error: {e}")
            raise

        self.logger.debug(f"{response.status_code} {method} /{url} ")

        if response.status_code >= 300:
            self.logger.error(f"request error: {response.status_code}", exc_info=True)
            raise Exception(response.json())

        return response.json()

    ######################################
    # Boilerplate code for httpx
    ######################################

    @wraps(httpx.Client.get)
    def get(self, url, **kwargs):
        """
        httpx.get wrapper
        """
        return self.request("GET", url, **kwargs)

    @wraps(httpx.Client.post)
    def post(self, url, **kwargs):
        """
        httpx.post wrapper
        """
        return self.request("POST", url, **kwargs)

    @wraps(httpx.Client.put)
    def put(self, url, **kwargs):
        """
        httpx.put wrapper
        """
        return self.request("PUT", url, **kwargs)

    @wraps(httpx.Client.request)
    def request(self, method, url, **kwargs):
        """
        httpx.request wrapper
        """
        response = self._request(method, url, **kwargs)

        return response

    ######################################
    ######################################
    ######################################
    ######################################
    ######################################

    def rounds(self):
        rounds = self.get("rounds/newway/")
        # rounds["rounds"] = [r for r in rounds["rounds"] if r["status"] != "ended"]
        return rounds

    def world(self):
        return self.get("play/newway/world/")

    def units(self):
        return self.get("play/newway/units/")

    def participate(self):
        return self.put("play/newway/participate/")

    def command(self, commands):
        return self.post("play/newway/command", json=commands)

    def test_world(self):
        return self.get("http://localhost:8000/")

    def test_submit(self, commands):
        return self.get("submit", json=commands)


if __name__ == "__main__":
    Fire(ApiClient("test"))
