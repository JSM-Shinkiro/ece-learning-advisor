# ECE Sample Plans and Next Implementation Notes

Team P07 · Reference review: October 22, 2026, Arizona time

These notes record useful sources and a possible next step. The sample plans have not been imported into the application.

## Source retrieval requirement

All saved PDFs, CSV exports, and screenshots are development references. The target app retrieves the relevant official information itself. Use these copies to understand source formats and check parser output, without requiring students or developers to maintain an uploaded course database.

Fetch the appropriate program plan and course entries on demand, respecting catalog year and delivery mode. Reuse a temporary cache and build the RAG index in memory. Show source links and retrieval dates, refresh expired information, and make source failures visible. Stored student progress is a separate concern. Automatic runtime source retrieval is still pending in the current prototype.

Prefer checking the relevant sources when a student submits a roadmap update or job search. If a content database becomes useful, it must refresh automatically on a configurable schedule as well. Background updates supplement checks during use. Reuse unchanged evidence and embeddings, record the last successful source check, and clearly label saved information when a live check fails. These freshness features remain planned work.

## Start with one ECE catalog year

Use the supplied **2026–27 B.S. in Electrical and Computer Engineering sample plan** to develop and verify the first automatic plan parser. It has a shared foundation on page 1, an Electrical option on page 2, and a Computer option on page 3. The advised sequence is dated January 2026. The deployed app should obtain the applicable plan from its official source.

The initial experience could ask for catalog year, completed courses, current enrollment, starting math placement, and Electrical, Computer, or Undecided option. Keep career interests such as AI/ML and embedded systems separate from the degree option. They can guide elective and outside learning suggestions while the ECE core stays tied to the selected program.

A few useful anchors from the supplied ECE map:

| Advised semester | ECE courses shown | Why this matters |
| --- | --- | --- |
| 2 | ECE 101 | Beginning programming appears within a broader math, physics, and writing foundation. |
| 3 | ECE 201 and ECE 274A | Include the ECE programming and digital logic sequence in a future catalog expansion. |
| 4 | ECE 220 | Circuits belong in the degree backbone even for a student interested in AI. |
| 5 onward | Separate Electrical and Computer option pages | Load the appropriate option rather than mixing their required courses. |

This is an excerpt, not the full curriculum or a prerequisite graph. Both option pages identify Advanced Standing as an enrollment condition. A student's freshman, sophomore, junior, or senior selection alone does not establish that status.

## What each source contributes

| Source | Useful content | How to use it |
| --- | --- | --- |
| Course catalog and saved CSV exports | Course identity, units, descriptions, and enrollment requirement references | Build course records and review academic rules. Resolve internal requirement IDs before interpreting them. |
| Saved program requirement PDFs | Required courses, alternatives, elective groups, and degree level | Define what a program requires for the applicable edition. |
| Four-year sample plans | Advised order, option branches, credit loads, and offering notes | Provide a reviewed baseline and explain typical progression. |
| Department flowcharts | Visual organization of courses and dependencies | Inform a future map view and identify rules that need catalog verification. |
| Degree Search and department overview pages | Program descriptions, related fields, and resource links | Support discovery and career context. Keep CS, CSE, and ECE as distinct programs. |
| Screenshots | Navigation, export workflow, and captured sample-plan layouts | Keep as reference evidence. Prefer underlying documents for ingestion and citations. |

The sample-plan headers direct students to the General Catalog for official requirements and warn that prerequisites can change. Placement in a later semester does not by itself establish a prerequisite. An empty prerequisite cell does not establish unrestricted enrollment.

## Official links worth keeping

| Resource | Link and review note |
| --- | --- |
| Engineering four-year plan directory | [Degree plans](https://engineering.arizona.edu/current/4-year-degree). The supplied screenshot shows 2026–27 and 2025–26 columns. The directory could not be fetched during this review, so the two supplied PDFs are the archived copies reviewed here. |
| ECSE school | [School homepage](https://ecse.engineering.arizona.edu/) and [undergraduate degrees](https://ecse.engineering.arizona.edu/undergrad-programs/degrees). The degree page links four-year plans, option flowcharts, online plans, and course resources. |
| ECE Computer option flowchart | [Department PDF](https://ecse.engineering.arizona.edu/sites/default/files/2025-09/CE_FlowChart_24-25.pdf). The page label and filename say 2024–25, but the PDF identifies catalogs beginning Fall 2025 and a 2025 revision. Preserve both labels until applicability is reviewed. |
| ECE Electrical option flowchart | [Department PDF](https://ecse.engineering.arizona.edu/sites/default/files/2025-09/EE_FlowChart_24-25.pdf). The PDF also identifies catalogs starting Fall 2025 and a 2025 revision despite its older filename. |
| Artificial Intelligence overview | [Degree Search](https://www.arizona.edu/degree-search/majors/artificial-intelligence). The supplied screenshots preserve its 2026 sample-plan view. Automated page extraction returned only the site footer during this review. |
| AI department resources | [AI B.S. page](https://cs.arizona.edu/aibs), [linked sample plan](https://drive.google.com/file/d/1MdhM27yJkFRbQSmHWss-ubmYEzBfxOFd/view), and [linked program checklist](https://drive.google.com/file/d/1OwY5uaD1ue2E-IoenRZCj_xVr4akU2up/view). The links were found on the department page. Their PDF contents were not reviewed here. |

## Details to preserve before importing

- Store program, catalog edition, delivery mode, option, advised semester, and source page with each plan entry. The engineering directory is described by ECSE as on-campus planning guidance. Review online plans separately.
- Represent named courses, alternative groups, general education slots, and technical elective slots as different entry types. Preserve course suffixes and source IDs as text. Split bundled alternatives only after reviewing their meaning.
- Keep the original requirement wording alongside any reviewed rule. Grade minimums, concurrent enrollment, placement, permission, and Advanced Standing need more information than a completed-course list.
- Keep offering notes with their source date. The Computer option labels ECE 369A and ECE 373 Fall Only. Confirm a current schedule before claiming a future offering.
- Keep elective approvals and overlap rules unresolved until checked. The plans mention possible general education overlap, but that does not authorize automatic double counting for any elective or minor.
- The AI screenshots contain `CSC 2XX`, `CSC 3XX`, and category labels such as Advanced AI. The department page currently names CSC 296 for Introduction to AI. Record this difference for edition review rather than automatically replacing a screenshot placeholder.
- The new engineering plans use ECE 101 and ECE 201. Do not infer equivalence with older course numbers from a similar title.

## A manageable next step

1. Verify an official download path for the ECE plan, then build a parser for its foundation and both options. Check the parsed rows against the saved PDF. Keep source pages and unresolved choices with each result.
2. Resolve named ECE courses through the official catalog and fetch their entries automatically. Use the saved course export to check extraction. Flag missing courses, conflicting units, and unresolved requirement references for review.
3. Show the selected template with completed and in-progress courses marked. Let students inspect remaining requirements and suggested next courses. Avoid promising a personalized graduation date.
4. Review a small set of prerequisite cases before labeling eligibility. Include alternatives, concurrent enrollment, minimum grades, and unknown Advanced Standing.
5. Retrieve the relevant course, requirement group, and plan entry through RAG. Use the model to explain recommendations with citations. Keep academic rule checks in deterministic code and preserve the existing unknown state when evidence is incomplete.

Start with this ECE template and the two existing career directions. Use CS, CSE, and AI materials as comparison and later expansion sources. Full schedule optimization, automatic transfer equivalencies, multiple minors, and graduate planning can follow after the baseline is reliable.

## Saved materials

- [Sample Plans](https://drive.google.com/drive/folders/1W2QnhMpHgNit3n3Fl63XXLXiImVPymjb): the supplied ECE and CSE 2026–27 PDFs.
- [Reference Screenshots](https://drive.google.com/drive/folders/149X0r31sV-qzURd20wD6x7JKy3G7MMsH): nine supplied screenshots with descriptive filenames.
- [Source inventory](09_CATALOG_SOURCES.md): individual files, original names, and catalog references.

Original PDF and image contents were preserved. Screenshot timestamps retain the supplied UTC date where present. A capture date is not a catalog effective date.
