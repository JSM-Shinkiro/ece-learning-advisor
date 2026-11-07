# Shared embedding-cache coordination

Implemented and verified November 6, 2026 MST (November 7 UTC). This backend change coordinates public document-vector cache builds across simultaneous requests in one Python server process. It prepares the existing app for a small shared pilot; it does not publish the app or establish multi-process coordination, real-user capacity, or answer quality.

## Problem and resulting behavior

Atomic file replacement already kept individual cache files complete. It did not stop two requests from both observing a cache miss and calling the document-embedding provider for the same public text. A controlled pre-change reproduction with two requests against the 34-chunk runtime collection made **68 document calls**, with both requests reporting a miss. This was a controlled adapter, with no real Gemini calls or credentials.

`EmbeddingCache.get` now holds a lock for the exact index path while it reads or builds that index. A queued caller rechecks the on-disk manifest after acquiring the lock and reuses a successful build. Each public document also has its own lock: requests using different source overlays can reuse identical document vectors while embedding changed text separately. Different models, dimensions, or cache directories retain distinct identities and can build independently. Existing manifest fields, format version, hashes, normalization, and atomic file writes remain unchanged; old compatible caches remain usable.

Locks are shared across cache instances using resolved paths. Only active locks remain in a guarded weak-reference registry, so successive source versions do not leave an unbounded list of idle locks. A request holds at most one index lock and one document lock, in that order, and releases them on success, failure, or interruption. Cache-write failure status is now local to each `get` invocation, including concurrent calls on the same cache instance.

All lock acquisitions share a deadline of 30 seconds from the start of the cache request. Once that deadline is reached, an immediately available lock can still be acquired, but another held lock cannot extend the wait. This bounds coordination waiting; it is not a total source/model-request timeout. Existing provider timeouts remain separate. A busy cache raises a sanitized `ProviderError`, allowing the existing controller/service behavior to show keyword retrieval and supported source information. Normal generation may still run through that existing fallback. A failed or unwritable cache can require a later request to embed again; failed results are not stored in a shared in-memory answer cache.

## Student and source boundaries

Only public document vectors and their existing cache manifests are shared. Query embeddings, student profiles, selected evidence contexts, generated selections/answers, provider clients, and keys remain request-local. Even identical student queries each make their own query-embedding request. Completion filtering, canonical statement validation, source timestamps, and academic unknowns still apply to each result.

On-use source checking stays before document-vector retrieval. A cache hit does not bypass the submitted request's source-refresh path or make a dated source current. The change introduces no profile store, background service, persistent content database, new academic interpretation, or provider retry policy. Multiple Python processes or host replicas may still duplicate builds; atomic replacement continues to protect complete individual files, but these process-local locks do not coordinate replicas.

## Verification

The complete suite passes **1,391 tests**, including **17 new concurrent-cache cases** and the existing **62 Streamlit interactions**. The new cases cover shared/separate cache instances, changed-source overlap, model/dimension/directory separation, owner failures and interruption, invalid-index repair, bounded index/document waits, fallback behavior, cumulative wait deadlines, per-request cache-write status, controller/profile isolation, idle-lock cleanup, path aliases, and sanitized path failures. Event/barrier controls force actual contention without relying on sleep-based timing assertions.

A separate Python 3.12.14 production-only check, without pytest installed, exercises the actual cache and controller with controlled seven-dimensional adapters and blocked HTTP clients:

| Controlled scenario | Document calls | Other observations |
| --- | ---: | --- |
| Two cold requests before the change | 68 | Two misses; duplicated the same 34 public chunks |
| Two cold requests after the change | 34 | One miss and one hit; vectors agree within floating-point tolerance |
| Two subsequent warm requests | 0 | Two hits |
| Two overlapping catalogs, one changed course description | 35 | Two separate indexes; 33 shared documents and two versions of the changed document |
| Eight concurrent controller requests | 34 | Seven hits/one miss; eight query calls, generations, closed clients, and controlled source-refresh invocations |

All eight controller results pass their canonical statement checks, retain separate contexts/answers and the correct profiles, and exclude recorded completed coursework. The probe checks 107 cache archives for public-document-only manifests. It makes **zero real model or HTTP requests**, uses no real credentials, and collects no participant judgments. These results measure controlled integration and call reuse, not live-provider load, billed savings, hosting availability, or relevance quality.

All eight production-readiness checks also pass, including real loopback server liveness and the app's credential-free offline roadmap. The [evidence](evidence/shared_cache_2026-11-06.json) retains the pre-change observation, production probe, readiness report, implementation hashes, and frozen-input fingerprints. Earlier actual Gemini and source observations retain their original scope and dates in [runtime provider verification](39_RUNTIME_PROVIDER_VERIFICATION.md).

The implementation uses Python's documented [lock acquire/release behavior](https://docs.python.org/3.12/library/threading.html#lock-objects) and [weak-value mappings](https://docs.python.org/3.12/library/weakref.html#weakref.WeakValueDictionary). No dependency is added. The production observation is Linux/Python 3.12; it does not assert a separately executed Windows concurrency test.

Independent grades for the prepared review packet, exact remaining ECE/edition evidence, a hosted single-process pilot, and final-report updates remain open. The midproject submission, frozen evaluation inputs, and 408 blank review grades remain unchanged.
