"""Shared bounded HTML/JSON downloads for configured public sources."""

import json
import time
from dataclasses import dataclass, field

import httpx

from .models import SourceAttempt

MAX_PAGE_BYTES = 3_000_000
REQUEST_TIMEOUT = httpx.Timeout(6.0, connect=4.0, pool=4.0)
SOURCE_SECONDS = 12.0
RETRY_DELAY = 0.25
RETRY_STATUSES = {502, 503, 504}
RETRY_EXCEPTIONS = (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout,
                    httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError)
_now, _pause = time.monotonic, time.sleep


class SourcePageError(ValueError):
    def __init__(self, message, http_status, location=None, *, retryable=False):
        super().__init__(message)
        self.http_status = http_status
        self.location = location if location and len(location) <= 2048 else None
        self.retryable = retryable


class SourceBudgetError(ValueError):
    """Elapsed guard expired; HTTPX still bounds each blocking phase separately."""


@dataclass
class SourceRequest:
    """One source job shares its retry, decoded-byte and elapsed guards.

    A resource's allowed redirect uses the same state. At most one retry is
    allowed, so a course/program uses up to two attempts and CS50 up to three.
    Elapsed checks are cooperative, not a hard cancellation of synchronous I/O.
    """
    attempts: list[SourceAttempt] = field(default_factory=list)
    retries: int = 0
    received_bytes: int = 0
    _started: float | None = field(default=None, repr=False)
    _finished: float | None = field(default=None, repr=False)
    _http_status: int | None = field(default=None, repr=False)

    def remaining(self):
        return SOURCE_SECONDS if self._started is None else SOURCE_SECONDS - (_now() - self._started)

    def ensure_time(self):
        if self.remaining() <= 0:
            raise SourceBudgetError("The source elapsed guard was exhausted")

    def begin(self):
        if self._started is None:
            self._started = _now()
        self.ensure_time()
        if len(self.attempts) >= 3:
            raise SourcePageError("The source attempt limit was reached", None)
        self._http_status = None
        return _now()

    def record(self, outcome, started, retry):
        self._finished = _now()
        self.attempts.append(SourceAttempt(outcome=outcome, http_status=self._http_status,
            seconds=max(0, self._finished - started), retry=retry))

    def apply(self, check):
        check.attempts = list(self.attempts)
        check.retry_count = sum(attempt.retry for attempt in self.attempts)
        check.transport_seconds = max(0, (self._finished or 0) - (self._started or 0)) if self._started is not None else 0
        if self.attempts:
            check.http_status = self.attempts[-1].http_status

    def diagnostics(self):
        """JSON-safe transport history; no response bodies or exception text."""
        return {"attempts": [a.model_dump(mode="json") for a in self.attempts],
            "retry_count": sum(a.retry for a in self.attempts),
            "transport_seconds": max(0, (self._finished or 0) - (self._started or 0)) if self._started is not None else 0,
            "http_status": self.attempts[-1].http_status if self.attempts else None}


@dataclass
class PublicPage:
    status: int
    text: str | None
    etag: str | None
    last_modified: str | None


def _read_once(client, url, headers, request, *, content_type="text/html", allow_not_modified=True):
    remaining = request.remaining()
    if remaining <= 0:
        raise SourceBudgetError("The source elapsed guard was exhausted")
    timeout = httpx.Timeout(**{key: min(value, remaining) for key, value in REQUEST_TIMEOUT.as_dict().items()})
    with client.stream("GET", url, headers=headers, timeout=timeout,
                       follow_redirects=False) as response:
        status = response.status_code
        request._http_status = status
        request.ensure_time()
        etag, modified = response.headers.get("etag"), response.headers.get("last-modified")
        etag = etag if etag and len(etag) <= 512 else None
        modified = modified if modified and len(modified) <= 100 else None
        if status == 304 and allow_not_modified:
            return PublicPage(status, None, etag, modified)
        media = response.headers.get("content-type", "").lower()
        matching_type = (media.split(";", 1)[0].strip() == content_type if content_type == "application/json"
                         else content_type in media)
        if status != 200 or not matching_type:
            raise SourcePageError("The official source page is unavailable", status, response.headers.get("location"),
                retryable=status in RETRY_STATUSES and "retry-after" not in response.headers)
        try:
            length = int(response.headers.get("content-length", "0"))
        except ValueError as exc:
            raise SourcePageError("The source response size is invalid", status) from exc
        if length < 0 or length > MAX_PAGE_BYTES - request.received_bytes:
            raise SourcePageError("The official page exceeds the download limit", status)
        body = bytearray()
        chunks = iter(response.iter_bytes())
        while True:
            request.ensure_time()
            try:
                chunk = next(chunks)
            except StopIteration:
                break
            request.received_bytes += len(chunk)
            if request.received_bytes > MAX_PAGE_BYTES:
                raise SourcePageError("The official page exceeds the request budget", status)
            body.extend(chunk)
            request.ensure_time()
        request.ensure_time()
        return PublicPage(status, body.decode("utf-8"), etag, modified)


def _read_with_recovery(client, url, headers, *, request=None, content_type="text/html", allow_not_modified=True):
    request = request if request is not None else SourceRequest()
    retry = False
    while True:
        started = request.begin()
        try:
            page = _read_once(client, url, headers, request,
                content_type=content_type, allow_not_modified=allow_not_modified)
        except (httpx.HTTPError, ValueError) as exc:
            kind = ("redirect" if isinstance(exc, SourcePageError) and exc.http_status in {301, 302, 303, 307, 308}
                    else "response" if isinstance(exc, SourcePageError) and exc.http_status == 304
                    else failure_kind(exc, request._http_status))
            request.record(kind, started, retry)
            transient = isinstance(exc, RETRY_EXCEPTIONS) or isinstance(exc, SourcePageError) and exc.retryable
            if (not transient or request.retries >= 1 or request.remaining() <= RETRY_DELAY
                    or request.received_bytes >= MAX_PAGE_BYTES):
                raise
            # Failed responses close before waiting. Rate limits, invalid pages,
            # and server-error responses carrying Retry-After are not retried.
            _pause(RETRY_DELAY)
            request._finished = _now()
            if request.remaining() <= 0:
                raise
            request.retries += 1
            retry = True
        else:
            request.record("not_modified" if page.status == 304 else "success", started, retry)
            return page


def read_public_page(client, url, headers, *, request=None):
    return _read_with_recovery(client, url, headers, request=request)


def read_public_json(client, url, headers, *, request=None):
    """Recover transport only; malformed/ambiguous JSON never triggers a retry."""
    page = _read_with_recovery(client, url, headers, request=request,
        content_type="application/json", allow_not_modified=False)
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Public JSON contains duplicate keys")
            result[key] = value
        return result
    def finite_constant(value):
        raise ValueError("Public JSON contains a nonfinite number")
    return json.loads(page.text, object_pairs_hook=unique_keys, parse_constant=finite_constant)


def failure_kind(exc, http_status):
    return ("timeout" if isinstance(exc, (httpx.TimeoutException, SourceBudgetError)) else
            "network" if isinstance(exc, httpx.HTTPError) else
            "response" if http_status not in {None, 200, 304} else "validation")
