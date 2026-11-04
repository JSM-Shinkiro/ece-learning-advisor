"""Shared bounded downloads for configured public academic sources."""

import time
from dataclasses import dataclass

import httpx

MAX_PAGE_BYTES = 3_000_000
REQUEST_TIMEOUT = httpx.Timeout(6.0, connect=4.0, pool=4.0)


class SourcePageError(ValueError):
    def __init__(self, message, http_status, location=None):
        super().__init__(message)
        self.http_status = http_status
        self.location = location if location and len(location) <= 2048 else None


@dataclass
class PublicPage:
    status: int
    text: str | None
    etag: str | None
    last_modified: str | None


def read_public_page(client, url, headers):
    started = time.monotonic()
    with client.stream("GET", url, headers=headers, timeout=REQUEST_TIMEOUT,
                       follow_redirects=False) as response:
        status = response.status_code
        etag, modified = response.headers.get("etag"), response.headers.get("last-modified")
        etag = etag if etag and len(etag) <= 512 else None
        modified = modified if modified and len(modified) <= 100 else None
        if status == 304:
            return PublicPage(status, None, etag, modified)
        if status != 200 or "text/html" not in response.headers.get("content-type", "").lower():
            raise SourcePageError("The official source page is unavailable", status, response.headers.get("location"))
        try:
            length = int(response.headers.get("content-length", "0"))
        except ValueError as exc:
            raise SourcePageError("The source response size is invalid", status) from exc
        if length > MAX_PAGE_BYTES:
            raise SourcePageError("The official page exceeds the download limit", status)
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > MAX_PAGE_BYTES or time.monotonic() - started > 12:
                raise SourcePageError("The official page exceeds the request budget", status)
        return PublicPage(status, body.decode("utf-8"), etag, modified)


def failure_kind(exc, http_status):
    return ("timeout" if isinstance(exc, httpx.TimeoutException) else
            "network" if isinstance(exc, httpx.HTTPError) else
            "response" if http_status not in {None, 200, 304} else "validation")
