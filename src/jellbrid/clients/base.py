import json
import urllib.parse

import httpx
import structlog
import tenacity

logger = structlog.get_logger(__name__)
client = httpx.AsyncClient(timeout=10.0)


class BaseClient:
    def __init__(self, url: str, headers: dict | None = None):
        self.base_url = url
        headers = headers or {}
        self.base_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        } | headers
        self.client = client

    @tenacity.retry(wait=tenacity.wait.wait_exponential_jitter())
    async def request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        json_: dict | None = None,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        if path.startswith("/"):
            logger.warning("Path will overwrite base path for request", path=path)

        headers = headers or {}
        headers.update(self.base_headers)

        url = urllib.parse.urljoin(self.base_url, path)
        response = await self.client.request(
            method, url, headers=headers, params=params, json=json_, data=data
        )

        logger.debug(f"{method} {response.request.url}", response=response.status_code)
        if response.status_code == 429:
            logger.warning(
                "Request was rate limited. Performing a retry with exponential backoff",
                error=response.json(),
            )
            raise tenacity.TryAgain
        if response.status_code >= 500:
            logger.warning(
                "Encountered server error. Performing a retry with exponential backoff",
                error=response.json(),
            )
            raise tenacity.TryAgain

        try:
            return response.json()
        except json.JSONDecodeError:
            # There was no return JSON to parse
            return {}
