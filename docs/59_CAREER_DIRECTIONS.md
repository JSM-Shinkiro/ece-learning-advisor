# Career directions and outside-ECE electives

Team P07 · November 14, 2026 MST

The Advisor offers five career directions and a combined collection of 31 courses and 11 resources. The published undergraduate ECE directory provides 78 searchable course entries. [Career course and source records](../data/reviewed/career_paths_2026_2027.json)

| Direction | Example learning progression | Role and application evidence | Outside-ECE elective candidate |
| --- | --- | --- | --- |
| Signals & Communications | ECE220 Basic Circuits → ECE340A Introduction to Communications → ECE429 Digital Signal Processing and ECE435A Digital Communications Systems | RF and DSP roles. Open radio networks give students a current application for signal processing and communications. [O*NET electronics engineers](https://www.onetonline.org/link/summary/17-2072.00) · [NTIA wireless test lab](https://its.ntia.gov/research/rat/communications-research-and-innovation-network/) | CSC425 Computer Networking adds protocol and routing concepts beyond the radio link. [Official course](https://catalog.arizona.edu/courses/0098201) |
| Controls & Robotics | ECE220 Basic Circuits → ECE320A Circuit Theory → ECE441A Automatic Control and ECE442 Digital Control Systems | Controls and robotics roles. Manufacturing automation and mobile robots use feedback and stability analysis. [O*NET robotics engineers](https://www.onetonline.org/link/summary/17-2199.08) · [Dated manufacturing co-op example](https://job-boards.greenhouse.io/rebuildmanufacturing/jobs/4734540005) | CSC437 Geometric Algorithms adds spatial reasoning for mapping and planning. [Official course](https://catalog.arizona.edu/courses/0098261) |
| Semiconductors & Digital Hardware | Design and verification use ECE274A, ECE369A, ECE407 and ECE462. Fabrication and test use ECE220, ECE351C, ECE352 and ECE446. | Digital design, verification, fab process and product test roles. Students can simulate a counter in Verilator, or use the fabrication and quality courses to explore process variation. [Verilator example](https://verilator.org/guide/latest/example_binary.html) · [Intel Arizona fab](https://www.intel.com/content/www/us/en/newsroom/news/client-computing/intel-unveils-panther-lake-architecture-first-ai-pc-platform-built-on-18a.html) · [Amkor packaging and test campus](https://ir.amkor.com/news-releases/news-release-details/amkor-technology-announces-phase-2-arizona-advanced-packaging) | SIE406 covers quality and process variation. MSE365 teaches the materials properties behind device behavior. [SIE406](https://catalog.arizona.edu/courses/0310781) · [MSE365](https://catalog.arizona.edu/courses/0228861) |

The 2026–27 program catalog specifies upper-division ECE coursework under Technical Electives I (R15492/L10). Technical Electives II (R15492/L20) lists 300- and 400-level coursework, excluding 390s and 490s. The advised plan directs students in both degree options to consult their major advisor for course approval. The app links each outside-ECE candidate to the elective guidance and separate section-enrollment information. [Program requirements](https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj) · [Advised degree plan](https://engineering.arizona.edu/pdfs/4-year-degree-plans/2026/ElectricalComputerEngineering26-27r.pdf)

## Advisor behavior

- Signals, Controls and Semiconductors load a versioned supplement by direction. Under **Still exploring**, a single match in the question can guide the roadmap. The student can save the matched direction.
- A design or fabrication question gives its study route priority in the semiconductor roadmap. The path panel shows both routes and links both outside-ECE candidates. Naming an elective can also bring its course card into the roadmap. Completed and currently taking courses are excluded from suggestions.
- The new direction works in **Courses & Resources** and with **Opportunities** title filters. The configured employer boards determine which jobs can appear in a search. The Verilator practice resource uses dated documentation.
- The combined collection has 51 evidence chunks. The archived independent-review inputs use the 34-chunk core and the original development comparison uses the ten-chunk baseline.

## Mathematics minor overlap

Open the card in **Courses & Resources**. It shows where the 2026–27 EE and CE plans overlap with the minor's calculus and foundation requirements, then lists linear algebra and upper-division coursework to check. It links the official requirements and the Math Center so students can confirm the rules for their catalog year. [Advised degree plan](https://engineering.arizona.edu/pdfs/4-year-degree-plans/2026/ElectricalComputerEngineering26-27r.pdf) · [Math Center](https://math.arizona.edu/academics/undergraduate/minors)

## Signals and Controls verification

Two source-only requests refreshed all six new course descriptions. Their first saved plans assembled in 10.9 ms (Signals) and 6.7 ms (Controls) on the server. The full requests took 6.21 s and 4.52 s in these individual observations. Both requests kept all recommended course rules unverified. [Source and software checks](evidence/career_directions_2026-11-14.json)

GitHub Actions passed 1,777 tests and nine startup checks on each OS, plus 38 Chromium checks. Chromium tested question-based direction selection, the official elective links, switching to Controls, and the collection's elective details at 390 pixels. The phone interaction used a local fragment update. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43646950094)

## Semiconductors and Mathematics verification

Three source-only requests exercised a chip-verification question with ECE369A already recorded, a fabrication question and a request for both outside-ECE courses. Across the requests, all five added course descriptions refreshed and the enrollment checks stayed unknown. The initial plans took 6.7–11.1 ms to assemble on the server. Source checks took 3.72–6.49 seconds. These are individual development observations with a fresh cache for each request. [Verification evidence](evidence/semiconductors_and_math_minor_2026-11-14.json)

The follow-up run passed 1,780 tests and nine startup checks per OS, plus 38 Chromium checks. The browser followed a fabrication question into the two elective links and opened MSE365 and Mathematics minor guidance at 390 pixels without a new Advisor request. The first run exposed a missing import in the browser assertion. The follow-up uses text matching for both new panels. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43683226351)
