# Expanded runtime coverage

Later November 6 follow-up: [expanded catalog review](38_EXPANDED_REVIEW_COLLECTIONS.md) now supports runtime/archived inputs and adds an operator catalog snapshot. The milestone below retains its original scope and measurements.

Implemented November 6, 2026 MST in the development repository. Submitted midproject artifacts and frozen evaluation inputs remain unchanged.

## Available collection

| Collection | Courses | Resources | Career mappings | Evidence chunks |
| --- | ---: | ---: | ---: | ---: |
| Frozen baseline | 5 | 2 | 2 | 10 |
| Expanded app | 17 | 6 | 2 | 29 |

`load_catalog()` still loads `data/reviewed/catalog.json`. The app, index builder, and production preflight use `load_runtime_catalog()`, adding `data/reviewed/runtime_extension.json`. The extension names its baseline corpus hash and edition. Replacement identities, duplicate courses/URLs, unsupported course editions, unknown provenance, and synthetic fixtures are rejected. Repeated loads return independent objects.

The baseline corpus hash remains `8df543f9bfe5d83374385ea5f756160d42144d9ab04bfc20b49e7f78059d643d`; the initial expanded hash is `977aaf386e805130a11d349cf7aac0349abe241de4d69f3b1bfa107d15853a3e`. Historical evaluation/provider-verification scripts and the external-review CLI retain the frozen collection. Their earlier measurements do not measure the expanded corpus. Separately bound review of the larger collection remains open.

All twelve added descriptions were checked against exact official course IDs, fixed units, the 2026–2027 edition, and links in configured visible program sections. Summaries are paraphrased; field provenance and enrollment reference IDs are retained.

| Added group | Courses |
| --- | --- |
| CS foundations/software | CSC110, CSC144, CSC210 |
| ECE foundations | ECE201, ECE220, ECE274A |
| ECE mathematics, ethics, circuits, and software | ECE310, ECE311, ECE320A, ECE340A, ECE351C, ECE373 |

The three added CS records reuse existing exact reviewed interpretations. CSC120 remains the fourth reviewed CS condition. All thirteen ECE course conditions remain unknown. Descriptive wording, opaque enrollment references, listed course links, or Engineering advanced-standing language cannot grant enrollment approval. Stages, directions, notes, and activities remain team preparation suggestions.

The novice default still starts with ECE101 when available; explicit foundation-course questions can select alternatives. Direction cards show a short example connection rather than chaining every course into an apparent sequence.

## Added official resources

| Resource | Bound source | Observed version | Preparation |
| --- | --- | --- | --- |
| Python Tutorial | [Python documentation](https://docs.python.org/3/tutorial/index.html) | 3.15.2 | Basic general programming knowledge |
| NumPy quickstart | [NumPy documentation](https://numpy.org/doc/stable/user/quickstart.html) | 2.5 | Python knowledge; excerpt lists example prerequisites |
| scikit-learn Getting Started | [scikit-learn documentation](https://scikit-learn.org/stable/getting_started.html) | 1.9.1 | Basic machine-learning practice |
| Raspberry Pi Pico C/C++ SDK | [Raspberry Pi documentation](https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html) | unversioned documentation | C/C++ practice and separate hardware/toolchain setup |

These join PyTorch and CS50. They are complementary preparation, not first-programming-course substitutes, university credit, or course equivalencies. Versions describe observed documentation, not catalog years or installed packages. The Pico page publishes no SDK release version, so none is invented.

Extraction requires the exact allowed URL, document identity, visible root, unique heading, and supported introductory section. Python uses its canonical `index.html` address; NumPy uses Prerequisites and Pico its named SDK section. Navigation, scripts, hidden content, code blocks, notices, edit links, and decorative SVG titles cannot become introductory evidence. Unsupported identity/version/layout fails closed to dated evidence. Existing conditional caches, hashes, dates, retry guards, and CS50-only redirect rules remain in place.

## Checks during use

The existing cap remains **eight course pages, two program pages, and two resource pages**, sharing three workers. A selected transient retry can add one attempt; CS50 alone permits one approved redirect. Elapsed/download guards are unchanged.

Saved-course checks prioritize explicit codes and reviewed phrases in mention order. When the collection exceeds the cap, reviewed prerequisite records come next; remaining ties favor unfinished coursework, then saved order. The trace records the version, requested/selected codes, reviewed-rule codes, phrase matches, and codes retained as snapshots. A checked program statement cannot make a skipped course description academically verified.

Discovery still uses verified program sections and remaining course slots. The current runtime snapshots already contain all configured linked identities. Resource names and reviewed whole phrases share one preference function between checking and context selection. The explicit question precedes interests, career scope still applies, and at most two named resources occupy the resource slots. Without an explicit match, existing ordering applies. This does not promise a new check for every saved/supporting record; each source keeps its own status. Ordinary rerenders do not fetch sources.

```powershell
.\.venv\Scripts\python.exe scripts/check_sources.py --collection runtime --career ai_ml --question "CSC210 with NumPy and scikit-learn"
.\.venv\Scripts\python.exe scripts/check_sources.py --collection runtime --career embedded --question "ECE373 with Pico and the Python tutorial"
```

The CLI defaults to `--collection baseline` for reproducibility. Its exit remains strict: expected budget skips also return failure because not all checks were verified. Inspect selected checks and snapshots separately. No model calls occur. The app/index builder use expanded coverage; fresh source overlays can require different vectors from saved paraphrases, handled by existing cache identity.

## Verification

All **1,261 tests pass**, including 23 runtime-collection cases, 55 expanded-resource cases, and 62 Streamlit interactions overall. Coverage includes frozen-input isolation, invalid extensions, provenance, ECE unknowns, four CS conditions sharing one program check, request/completion priority, omitted-course freshness, resource layouts/caches/304/failures, named-resource/context alignment, and actual expanded app startup. Historical five-course UI scenarios remain explicitly isolated; the added UI case and production smoke use real expanded defaults.

The Python 3.12 production-only environment passes all eight readiness checks, including loopback health and an offline roadmap with external HTTP blocked. Its first smoke failed the ECE101 expectation after broader keyword competition selected CSC110 by default. Explicit default-foundation preference restores the intended novice behavior; the follow-up passes. Both observations are retained.

[Dated evidence](evidence/runtime_coverage_2026-11-06.json) retains inspection, source checks, follow-ups, and runtime outcomes. Initial program downloads succeeded but an inspection script passed an extra parser argument. Corrected parsing of those saved pages validated their selected links; this was not an application source failure.

| Live observation | Selected checks | Result | Backend time |
| --- | ---: | --- | ---: |
| AI/ML: CSC210, ECE310, NumPy, scikit-learn | 12 | All selected sources passed; context still chose saved PyTorch instead of requested NumPy | 13.092 s |
| Embedded: ECE373, Pico, Python | 11 | All selected sources passed; both requested resources appeared verified | 11.829 s |
| One AI/ML follow-up after shared resource preference | 12 | All selected sources passed; verified NumPy and scikit-learn appeared in context | 14.559 s |

All three used zero model calls and no credentials; requests succeeded on first attempts. Omitted records remained snapshots. CSC210's recorded CSC120 grade branch was satisfied in the AI case; ECE conditions stayed unknown. These are dated source/application checks, not independent relevance judgments, model accuracy, latency benchmarks, full-catalog coverage, or complete enrollment approval.

## Remaining work

The original ambition of 20–30 courses and 8–12 resources remains open: current coverage is 17 and six. Broaden coverage where useful for the demonstration, seek exact ECE condition evidence/other editions, and prepare separate judgments for the larger corpus. Student review, hosting, durable authenticated profiles, and final presentation/report work remain separate milestones. No permanent content database was added; if introduced, it must refresh on a configurable schedule as well as during use.
