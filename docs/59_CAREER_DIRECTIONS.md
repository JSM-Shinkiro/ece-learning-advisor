# Career directions and outside-ECE electives

Team P07 · Updated November 15, 2026 MST

The Advisor offers eight career directions, 17 specialization choices and a combined collection of 47 courses and 16 resources. Open a career panel in **My Roadmap** to see the specialization choices, course sequences and practice exercises. The published undergraduate ECE directory provides 78 searchable course entries. [Career course and source records](../data/reviewed/career_paths_2026_2027.json)

| Direction | Specializations | Selected course anchors and complementary sources |
| --- | --- | --- |
| AI / Machine Learning | Computer Vision & Perception · Applied ML · Edge AI & On-Device Inference | ECE425, [CSC477](https://catalog.arizona.edu/courses/0098501) and [CSC480](https://catalog.arizona.edu/courses/0421321). |
| Embedded Systems | Firmware & Real-Time Systems · Edge AI & On-Device Inference | ECE369A, ECE372A and [ECE402C](https://catalog.arizona.edu/courses/0436591). Use [FreeRTOS](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/01-Tasks-and-co-routines/00-Tasks-and-co-routines) for scheduling practice and [LiteRT](https://developers.google.com/edge/litert/conversion/tensorflow/quantization/post_training_quantization) for Edge AI. |
| Signals & Communications | DSP & Wireless Communications · RF & Microwave Engineering | ECE429 and ECE435A support DSP and wireless. ECE381A, [ECE486](https://catalog.arizona.edu/courses/0122141), [ECE488](https://catalog.arizona.edu/courses/0122161) and [ECE484](https://catalog.arizona.edu/courses/0122081) support RF and microwave work. [CSC425](https://catalog.arizona.edu/courses/0098201) covers networking beyond the radio link. |
| Controls & Robotics | Industrial Automation & Motion Control · Robotics & Autonomy | ECE441A, ECE442 and [ECE447A](https://catalog.arizona.edu/courses/0325232) develop motion and feedback topics. [CSC437](https://catalog.arizona.edu/courses/0098261) adds spatial planning concepts for robotics. |
| Semiconductors & Digital Hardware | Design & verification · Fabrication & test | ECE407 and ECE462 cover design topics. ECE352 and ECE446 cover devices and fabrication. [SIE406](https://catalog.arizona.edu/courses/0310781) adds quality engineering and [MSE365](https://catalog.arizona.edu/courses/0228861) adds materials physics. [Verilator example](https://verilator.org/guide/latest/example_binary.html) |
| Photonics & Electro-Optics | Imaging & Optical Systems · Lasers & Optical Communications | ECE381A and [ECE459](https://catalog.arizona.edu/courses/0121751) support imaging. [ECE370](https://catalog.arizona.edu/courses/0249862) and [ECE430](https://catalog.arizona.edu/courses/0121512) support lasers and communications. [OPTI300](https://catalog.arizona.edu/courses/0379691) adds practical optics. [Wyant photonics examples](https://optics.arizona.edu/research/research-specialties/photonics) |
| Power & Energy Systems | Solar PV & Energy Storage · Building Electrical Systems | ECE320A, [ECE414A](https://catalog.arizona.edu/courses/0121391), and [ARCE320](https://catalog.arizona.edu/courses/0401421). The department lists ENGR 211M for ARCE320. Storage concepts use the [DOE learning resource](https://www.energy.gov/cmei/systems/solar-integration-solar-energy-and-storage-basics). |
| Biomedical Instrumentation & Sensors | Biosignals & Instrumentation · Biomedical Imaging | [ECE417](https://catalog.arizona.edu/courses/0093732) and [BME330](https://catalog.arizona.edu/courses/0363371) support sensing and measurement. ECE429 and [BME416](https://catalog.arizona.edu/courses/0093721) support imaging. BME416 lists College of Engineering Advanced Standing or department consent. |

The 2026–27 program catalog specifies upper-division ECE coursework under Technical Electives I (R15492/L10). Technical Electives II (R15492/L20) lists 300- and 400-level coursework, excluding 390s and 490s. The advised plan directs students in both degree options to consult their major advisor for course approval. The app links each outside-ECE candidate to the elective guidance and separate section-enrollment information. [Program requirements](https://catalog.arizona.edu/programs/ECEBSECE/program-requirements-a1nCj) · [Advised degree plan](https://engineering.arizona.edu/pdfs/4-year-degree-plans/2026/ElectricalComputerEngineering26-27r.pdf)

## Advisor behavior

- A question can match a direction under **Still exploring**. Inside a direction, use an **Explore** button or name a specialization in the question field to focus the roadmap. Edge AI appears in both AI / Machine Learning and Embedded Systems.
- A selected route supplies relevant courses and its available practice resource. Explicit course requests can join the route. Recorded completed and current courses are excluded from suggestions. Academic enrollment checks use the available section and catalog evidence.
- All eight directions work in **Courses & Resources** and with **Opportunities** title filters. The configured employer boards determine which jobs appear in a search.
- The combined collection has 75 evidence chunks. The archived independent-review inputs use the 34-chunk core and the original development comparison uses the ten-chunk baseline.

The power routes cover a foundation in solar generation, storage and building power. A dedicated utility-grid protection route still needs a verified course sequence.

## Mathematics minor overlap

Open the card in **Courses & Resources**. It shows where the 2026–27 EE and CE plans overlap with the minor's calculus and foundation requirements, then lists linear algebra and upper-division coursework to check. It links the official requirements and the Math Center so students can confirm the rules for their catalog year. [Advised degree plan](https://engineering.arizona.edu/pdfs/4-year-degree-plans/2026/ElectricalComputerEngineering26-27r.pdf) · [Math Center](https://math.arizona.edu/academics/undergraduate/minors)

## Signals and Controls verification

Two source-only requests refreshed all six new course descriptions. Their first saved plans assembled in 10.9 ms (Signals) and 6.7 ms (Controls) on the server. The full requests took 6.21 s and 4.52 s in these individual observations. Both requests kept all recommended course rules unverified. [Source and software checks](evidence/career_directions_2026-11-14.json)

GitHub Actions passed 1,777 tests and nine startup checks on each OS, plus 38 Chromium checks. Chromium tested question-based direction selection, the official elective links, switching to Controls, and the collection's elective details at 390 pixels. The phone interaction used a local fragment update. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43646950094)

## Semiconductors and Mathematics verification

Three source-only requests exercised a chip-verification question with ECE369A already recorded, a fabrication question and a request for both outside-ECE courses. Across the requests, all five added course descriptions refreshed and the enrollment checks stayed unknown. The initial plans took 6.7–11.1 ms to assemble on the server. Source checks took 3.72–6.49 seconds. These are individual development observations with a fresh cache for each request. [Verification evidence](evidence/semiconductors_and_math_minor_2026-11-14.json)

The follow-up run passed 1,780 tests and nine startup checks per OS, plus 38 Chromium checks. The browser followed a fabrication question into the two elective links and opened MSE365 and Mathematics minor guidance at 390 pixels without a new Advisor request. The first run exposed a missing import in the browser assertion. The follow-up uses text matching for both new panels. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43683226351)

## Specialization verification

Eight source-only requests refreshed the 16 new course records from the official catalog. A separate Biomedical Imaging request verified that the route includes both ECE429 and BME416. BME416 displays its published enrollment condition and leaves individual eligibility unverified. [Source and coverage evidence](evidence/career_specializations_2026-11-14.json)

GitHub Actions passed 1,803 tests and nine startup checks on each OS, plus 39 Chromium checks. Chromium followed a photonics question to the Lasers route, switched to Imaging using **Explore**, and opened the BME416 details and elective link at 390 pixels. [Passing run](https://github.com/JSM-Shinkiro/ece-learning-advisor/actions/runs/43688855340)
