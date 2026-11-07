"""Request-local, fixed-label progress; UI observers never control advisor results."""

from __future__ import annotations

import time


PHASE_LABELS = {
    "request": "Checking your learning goal",
    "sources": "Checking official sources",
    "snapshots": "Using saved source snapshots",
    "ai_setup": "Starting AI assistance",
    "embeddings": "Preparing source search",
    "ranking": "Finding learning options",
    "requirements": "Checking recorded preparation",
    "generation": "Preparing AI explanations",
    "validation": "Checking explanations against the sources",
}


class RequestProgress:
    """Record sequential phase boundaries on the request thread, without user text.

    Each callback receives a fixed phase ID/label. A faulty observer is disabled;
    it cannot fail a successful request or cause a second provider/source call.
    Times run through final result assembly, excluding provider cleanup/rendering.
    """

    def __init__(self, callback=None, *, clock=None):
        self.clock = clock or time.perf_counter
        self.started = self.clock()
        self.callback = callback
        self.phases = []
        self.observer_failed = False
        self.finished = None

    def start(self, phase):
        if phase not in PHASE_LABELS:
            raise ValueError("Unknown request phase")
        if self.finished is not None or (self.phases and self.phases[-1]["phase"] == phase):
            return
        elapsed = max(0.0, self.clock() - self.started)
        if self.phases:
            self.phases[-1]["seconds"] = max(0.0, elapsed - self.phases[-1]["started_seconds"])
        self.phases.append({"phase": phase, "label": PHASE_LABELS[phase],
                            "started_seconds": elapsed, "seconds": 0.0})
        if self.callback is not None:
            try:
                self.callback(phase, PHASE_LABELS[phase])
            except Exception:
                self.observer_failed = True
                self.callback = None

    def finish(self):
        if self.finished is None:
            self.finished = max(0.0, self.clock() - self.started)
            if self.phases:
                self.phases[-1]["seconds"] = max(0.0, self.finished - self.phases[-1]["started_seconds"])
        return {"version": "p07-request-phases-v1", "elapsed_seconds": self.finished,
                "scope": "controller_until_result_before_provider_cleanup_and_browser_rendering",
                "observer_failed": self.observer_failed,
                "phases": [dict(phase) for phase in self.phases]}
