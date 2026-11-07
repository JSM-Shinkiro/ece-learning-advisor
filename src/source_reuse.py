"""Short, bounded reuse of public evidence successfully checked by this process.

Disk caches alone never grant freshness. A lease is issued only after a successful
check and cache write, and is matched against the validated disk entry on reuse.
No profiles, queries, rankings or answers are stored here.
"""

from collections import OrderedDict
from pathlib import Path
from threading import Lock
import time

SOURCE_REUSE_SECONDS = 300
VERIFIED_CHECKS = frozenset({"updated", "unchanged", "not_modified", "recent_cache"})


def validate_reuse_seconds(value):
    if type(value) is not int or not 0 <= value <= SOURCE_REUSE_SECONDS:
        raise ValueError("Source reuse must be an integer from 0 to 300 seconds")
    return value


class RecentSourceChecks:
    def __init__(self, *, clock=None, max_entries=256):
        self.clock = clock or time.monotonic
        self.max_entries = max_entries
        self.entries = OrderedDict()
        self.lock = Lock()

    @staticmethod
    def identity(saved):
        return saved.content_hash, saved.retrieved_at, saved.last_checked_at

    def remember(self, path, saved):
        key = Path(path).resolve()
        with self.lock:
            self.entries[key] = self.identity(saved), self.clock()
            self.entries.move_to_end(key)
            while len(self.entries) > self.max_entries:
                self.entries.popitem(last=False)

    def forget(self, path):
        with self.lock:
            self.entries.pop(Path(path).resolve(), None)

    def reuse(self, path, saved, check, seconds):
        validate_reuse_seconds(seconds)
        key = Path(path).resolve()
        with self.lock:
            lease = self.entries.get(key)
            valid = (seconds > 0 and saved is not None and lease is not None
                and lease[0] == self.identity(saved)
                and 0 <= self.clock() - lease[1] < seconds
                and 0 <= (check.attempted_at - saved.last_checked_at).total_seconds() < seconds)
            if not valid:
                self.entries.pop(key, None)
                return False
        check.status = "recent_cache"
        check.retrieved_at, check.last_checked_at = saved.retrieved_at, saved.last_checked_at
        check.content_hash = saved.content_hash
        return True


recent_sources = RecentSourceChecks()
