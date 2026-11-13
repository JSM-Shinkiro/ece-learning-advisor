"""Bounded, session-owned advisor work. Workers never access Streamlit state.

The only process-wide resource is a four-slot admission semaphore. Results and
progress belong to the job held by its browser session, with no shared job map.
"""

from dataclasses import dataclass
from hashlib import sha256
from threading import BoundedSemaphore, Event, Lock, Thread
from uuid import uuid4

from .progress import AdvisorCancelled, PHASE_LABELS

_SLOTS = BoundedSemaphore(4)


class AdvisorBusy(RuntimeError):
    pass


def source_checks_pending(result):
    return result is not None and result.trace.get("source_refresh", {}).get("reason") == "pending"


def profile_identity(profile):
    return sha256(profile.model_dump_json().encode()).hexdigest()


@dataclass(frozen=True)
class JobSnapshot:
    version: int
    result: object
    phases: tuple[str, ...]
    done: bool
    failed: bool
    cancelled: bool


class AdvisorJob:
    def __init__(self, profile):
        self.request_id = uuid4().hex
        self.profile_identity = profile_identity(profile)
        self._lock = Lock()
        self._cancelled = Event()
        self._finished = Event()
        self._version = 0
        self._result = None
        self._phases = []
        self._done = self._failed = False

    def __repr__(self):
        return f"AdvisorJob(request_id={self.request_id!r})"

    def is_cancelled(self):
        return self._cancelled.is_set()

    def cancel(self):
        with self._lock:
            self._cancelled.set()
            self._result = None

    def progress(self, phase, label):
        if phase not in PHASE_LABELS or label != PHASE_LABELS[phase]:
            return
        with self._lock:
            if not self.is_cancelled() and (not self._phases or self._phases[-1] != phase):
                self._phases.append(phase)

    def publish(self, result, *, done=False):
        with self._lock:
            if self.is_cancelled() or profile_identity(result.context.profile) != self.profile_identity:
                if done:
                    self._failed = self._done = True
                return
            self._result = result
            self._version += 1
            self._done = done

    def fail(self):
        with self._lock:
            self._failed = self._done = True

    def snapshot(self):
        with self._lock:
            return JobSnapshot(self._version, self._result, tuple(self._phases),
                self._done, self._failed, self.is_cancelled())

    def wait(self, timeout=0):
        """Bounded lifecycle observation for checks; the UI only polls snapshots."""
        return self._finished.wait(timeout)


def start_advisor_job(catalog, profile, *, runner=None, slots=None, **options):
    from .controller import run_advisor
    slots = _SLOTS if slots is None else slots
    if not slots.acquire(blocking=False):
        raise AdvisorBusy()
    try:
        job = AdvisorJob(profile)
        owned_catalog, owned_profile = catalog.model_copy(deep=True), profile.model_copy(deep=True)
        def work():
            try:
                result = (runner or run_advisor)(owned_catalog, owned_profile, **options,
                    progress=job.progress, on_plan=job.publish, cancelled=job.is_cancelled)
                job.publish(result, done=True)
            except AdvisorCancelled:
                job.cancel()
            except BaseException:
                # No exception strings, frames, credentials or profile data cross
                # this boundary, including failures during provider cleanup.
                job.fail()
            finally:
                slots.release()
                job._finished.set()
        Thread(target=work, name="ece-advisor-request", daemon=True).start()
        return job
    except BaseException:
        slots.release()
        raise


def discard_advisor_job(state):
    job = state.pop("advisor_job", None)
    if job is not None:
        job.cancel()
    state.pop("advisor_job_version", None)
    state.pop("advisor_activity", None)


def collect_advisor_job(state, job):
    """Only the session's current request for its current profile can apply."""
    if state.get("advisor_job") is not job:
        return False
    if profile_identity(state["profile"]) != job.profile_identity:
        discard_advisor_job(state)
        state.pop("result", None)
        return True
    snapshot = job.snapshot()
    changed = False
    if snapshot.result is not None and snapshot.version > state.get("advisor_job_version", 0):
        state["result"] = snapshot.result
        state["advisor_job_version"] = snapshot.version
        changed = True
    if snapshot.done or snapshot.cancelled:
        result = state.get("result")
        state["advisor_activity"] = {
            "label": "The plan could not be updated" if snapshot.failed and result is None else
                "More detail needed" if result is not None and (result.coverage_notice or result.generation_status == "insufficient_evidence")
                else "Learning plan ready",
            "phases": snapshot.phases,
            "error": snapshot.failed and result is None,
            "notice": (
                "Source checks could not finish. Your saved-data plan is still available."
                if source_checks_pending(result) else
                "AI assistance could not finish. Your source plan is still available."
            ) if snapshot.failed and result is not None else None,
        }
        state.pop("advisor_job", None)
        state.pop("advisor_job_version", None)
        changed = True
    return changed


def keep_source_plan(state):
    job = state.get("advisor_job")
    result = state.get("result")
    if job is None or result is None or profile_identity(state["profile"]) != job.profile_identity:
        return
    phases = job.snapshot().phases
    notice = ("Source checks stopped. Your saved-data plan is ready to use." if source_checks_pending(result)
              else "AI assistance stopped. Your source plan is ready to use.")
    discard_advisor_job(state)
    state["advisor_activity"] = {"label": "Learning plan ready", "phases": phases, "error": False,
        "notice": notice}
