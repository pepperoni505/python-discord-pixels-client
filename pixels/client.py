import requests
import logging
import coloredlogs
import asyncio

API_URL = "https://pixels.pythondiscord.com"

RATELIMIT_CODE = 429
SUCCESS_CODE = 200

logger = logging.getLogger(__name__)

coloredlogs.install(level='DEBUG', logger=logger)

class RateLimitter:

    def __init__(self, client, endpoint):
        self.client = client
        self.endpoint = endpoint
        self.requests_remaining = None
        self.requests_limit = None
        self.requests_period = None
        self.requests_reset = None

        self.cooldown = None

    def update(self, headers):
        if 'requests-remaining' in headers:
            self.requests_remaining = headers['requests-remaining']
        if 'requests-limit' in headers:
            self.requests_limit = headers['requests-limit']
        if 'requests-period' in headers:
            self.requests_period = headers['requests-period']
        if 'requests-reset' in headers:
            self.requests_reset = headers['requests-reset']

        if 'Cooldown-Reset' in headers:
            self.cooldown = int(headers['Cooldown-Reset'])

    async def pause(self):
        if self.cooldown is not None:
            logger.error(f'Ratelimit exceeded, sleeping for {self.cooldown}s for endpoint {self.endpoint}')
            await asyncio.sleep(self.cooldown)
        

class Client:

    def __init__(self, token):
        self.token = token

        self.HEADERS = {
            "Authorization": f"Bearer {self.token}"
        }

        self.RateLimiters = {}

    async def get_pixel(self, coords):
        data = {
            "x": coords[0],
            "y": coords[1]
        }

        result = requests.get(
            API_URL + "/get_pixel",
            params=data,
            headers=self.HEADERS
        )

        if "/get_pixel" not in self.RateLimiters:
            self.RateLimiters["/get_pixel"] = RateLimitter(self, "/get_pixel")
        self.RateLimiters["/get_pixel"].update(result.headers)

        if result.status_code == RATELIMIT_CODE:
            await self.RateLimiters["/get_pixel"].pause()
            return await self.get_pixel(coords)
        elif result.status_code == SUCCESS_CODE:
            logger.debug(f"pixel at x={coords[0]},y={coords[1]} is color {result.json()['rgb']}")
            return result.json()['rgb']
        else:
            result.raise_for_status()

    async def get_pixels(self):
        result = requests.get(
            API_URL + "/get_pixels",
            headers=self.HEADERS
        )

        if "/get_pixels" not in self.RateLimiters:
            self.RateLimiters["/get_pixels"] = RateLimitter(self, "/get_pixels")
        self.RateLimiters["/get_pixels"].update(result.headers)

        if result.status_code == RATELIMIT_CODE:
            await self.RateLimiters["/get_pixels"].pause()
            return await self.get_pixels()
        elif result.status_code == SUCCESS_CODE:
            return result.content
        else:
            result.raise_for_status()

    async def get_size(self):
        result = requests.get(
            API_URL + "/get_size"
        )

        if "/get_size" not in self.RateLimiters:
            self.RateLimiters["/get_size"] = RateLimitter(self, "/get_size")
        self.RateLimiters["/get_size"].update(result.headers)

        if result.status_code == RATELIMIT_CODE:
            await self.RateLimiters["/get_size"].pause()
            return await self.get_size()
        elif result.status_code == SUCCESS_CODE:
            return result.json()['height'], result.json()['width'] 
        else:
            result.raise_for_status()

    async def set_pixel(self, coords, rgb):
        data = {
            "x": coords[0],
            "y": coords[1],
            "rgb": rgb
        }

        result = requests.post(
            API_URL + "/set_pixel",
            json=data,
            headers=self.HEADERS
        )

        if "/set_pixel" not in self.RateLimiters:
            self.RateLimiters["/set_pixel"] = RateLimitter(self, "/set_pixel")
        self.RateLimiters["/set_pixel"].update(result.headers)

        if result.status_code == RATELIMIT_CODE:
            await self.RateLimiters["/set_pixel"].pause()
            return await self.set_pixel(coords, rgb)
        elif result.status_code == SUCCESS_CODE:
            logger.debug(result.json()["message"])
        else:
            result.raise_for_status()
