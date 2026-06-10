"""Small stdlib HTTP client for Elasticsearch.

The project keeps this dependency-free for now. It can be replaced with the official
Elastic Python client later without changing higher-level storage code.
"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agentguard.storage.elastic_config import ElasticConfig


class ElasticHttpError(RuntimeError):
    pass


class ElasticHttpClient:
    def __init__(self, config: ElasticConfig):
        config.require_configured()
        self.config = config
        self.base_url = str(config.url).rstrip("/")

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def head(self, path: str) -> bool:
        try:
            self.request("HEAD", path)
        except ElasticHttpError as exc:
            if "-> 404:" in str(exc):
                return False
            raise
        return True

    def put(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", path, json_body=body)

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, json_body=body)

    def post_ndjson(self, path: str, lines: list[dict[str, Any]]) -> dict[str, Any]:
        payload = "".join(json.dumps(line, separators=(",", ":")) + "\n" for line in lines)
        return self.request("POST", path, ndjson_body=payload)

    def request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
        ndjson_body: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        body: bytes | None = None
        headers = self._headers()
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if ndjson_body is not None:
            body = ndjson_body.encode("utf-8")
            headers["Content-Type"] = "application/x-ndjson"

        request = Request(url=url, method=method, data=body, headers=headers)
        try:
            with urlopen(  # noqa: S310 - URL comes from local developer config.
                request,
                timeout=self.config.request_timeout_seconds,
            ) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise ElasticHttpError(
                f"Elastic request failed: {method} {path} -> {exc.code}: {error_body}"
            ) from exc

        return json.loads(payload) if payload else {}

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"ApiKey {self.config.api_key}"
        elif self.config.username and self.config.password:
            token = f"{self.config.username}:{self.config.password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(token).decode("ascii")
        return headers
