# Retrieval relevance review

Packet: `p07-runtime-review-v1`
Packet fingerprint: `8942e29a4c7279d771fdbd7e5b4a1d016a88b4a56354f9a9866d895a3f4d5229`
Corpus fingerprint: `bdd87ede10f6c020b1833f4d43653e62207ab372f912bde81691c829f0db13f7`
Catalog snapshot fingerprint: `bfbc448044df4eea9d2cde260f1e06e3f21f1296a239a5e168fe939dc0224758`
Saved evidence: 34 chunks from 30 sources.
Review workload: 12 questions × 34 chunks = 408 grades.

Read the saved evidence below, then fill review_template.json. Use an alias; no name or email is needed.
Set reviewer_role to independent_reviewer, project_contributor, or controlled_fixture, and reviewed_at to an ISO timestamp with timezone.
Grade every chunk for every question. null means unfinished, not irrelevant. Optional notes can explain uncertainty.

| Grade | Meaning |
| --- | --- |
| 0 | Unrelated |
| 1 | Broad background |
| 2 | Useful supporting evidence |
| 3 | Direct evidence |

All-zero judgments are allowed when nothing in this collection helps answer the question.
Candidate order is shuffled, not ranked. Prior grades, expected answers, scores, and aliases are omitted.
Judge the saved text. Source links are for provenance; live pages may differ from this dated snapshot.
Question origin: custom_questions_unverified. Existing development questions are not held out.
A completed form does not authenticate reviewer independence or establish answer correctness.

## Questions

### edge-hardware

I want to put small machine-learning models on hardware. What should I study first?

Candidate order:

`resource:cs50:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:CSC110:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `career:ai_ml:overview`, `uofa:ECE310:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `resource:sklearn:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `resource:pico:overview`, `uofa:ECE340A:2026-2027:overview`, `resource:pytorch:overview`, `uofa:ECE201:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:ECE425:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `resource:numpy:overview`, `uofa:ECE372A:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `resource:mit_structures:overview`, `resource:python:overview`, `career:embedded:overview`, `uofa:ECE311:2026-2027:overview`

### software-quality

How can I learn to organize a bigger program and write unit tests?

Candidate order:

`uofa:CSC110:2026-2027:overview`, `uofa:ECE311:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`, `resource:mit_algorithms:overview`, `resource:python:overview`, `uofa:ECE310:2026-2027:overview`, `resource:cs50:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `resource:numpy:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `career:ai_ml:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `resource:pytorch:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:ECE373:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:ECE381A:2026-2027:overview`, `resource:pico:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `career:embedded:overview`, `uofa:CSC120:2026-2027:overview`, `resource:sklearn:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`

### engineering-math

Which learning activities connect linear algebra and probability with engineering?

Candidate order:

`career:ai_ml:overview`, `resource:pico:overview`, `uofa:ECE311:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:ECE320A:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `resource:sklearn:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE101:2026-2027:overview`, `resource:pytorch:overview`, `resource:numpy:overview`, `resource:mit_algorithms:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:ECE425:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `career:embedded:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `resource:python:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:ECE310:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`

### device-physics

I want to understand semiconductor behavior and electronic devices.

Candidate order:

`resource:pico:overview`, `uofa:ECE201:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `resource:mit_structures:overview`, `resource:pytorch:overview`, `resource:sklearn:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE310:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:ECE351C:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `resource:cs50:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:CSC144:2026-2027:overview`, `resource:python:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:ECE311:2026-2027:overview`, `career:embedded:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `career:ai_ml:overview`, `uofa:ECE372A:2026-2027:overview`, `resource:numpy:overview`, `uofa:CSC120:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`

### fields-and-waves

Where can I study electric and magnetic fields and transmission lines?

Candidate order:

`uofa:CSC210:2026-2027:rule:R1299-L70`, `career:embedded:overview`, `resource:pytorch:overview`, `uofa:ECE311:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE310:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:ECE425:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:ECE372A:2026-2027:overview`, `resource:numpy:overview`, `resource:cs50:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `resource:python:overview`, `uofa:ECE340A:2026-2027:overview`, `resource:sklearn:overview`, `resource:pico:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:CSC120:2026-2027:overview`, `career:ai_ml:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:CSC372:2026-2027:overview`

### language-choices

I would like to compare programming languages and how they express the same task.

Candidate order:

`uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `career:embedded:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE310:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `resource:pytorch:overview`, `uofa:ECE369A:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:CSC372:2026-2027:overview`, `resource:numpy:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `resource:python:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:ECE373:2026-2027:overview`, `resource:sklearn:overview`, `resource:pico:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `career:ai_ml:overview`, `uofa:ECE311:2026-2027:overview`

### numerical-arrays

I already use Python and want to practice with numerical arrays.

Candidate order:

`uofa:ECE340A:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `resource:pytorch:overview`, `resource:pico:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE274A:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `resource:python:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `career:embedded:overview`, `resource:numpy:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `resource:sklearn:overview`, `uofa:ECE310:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `career:ai_ml:overview`, `uofa:ECE311:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:CSC120:2026-2027:overview`

### model-evaluation

How should I practice preprocessing data and evaluating machine-learning predictions?

Candidate order:

`uofa:CSC120:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `career:embedded:overview`, `uofa:ECE101:2026-2027:overview`, `resource:python:overview`, `uofa:ECE311:2026-2027:overview`, `resource:pico:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:ECE425:2026-2027:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `resource:pytorch:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `resource:cs50:overview`, `resource:numpy:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:ECE201:2026-2027:overview`, `career:ai_ml:overview`, `resource:sklearn:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:ECE310:2026-2027:overview`, `resource:mit_structures:overview`

### microcontroller-project

I want a small C/C++ microcontroller project using a Pico board.

Candidate order:

`uofa:ECE373:2026-2027:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `uofa:ECE311:2026-2027:overview`, `career:ai_ml:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `career:embedded:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:ECE201:2026-2027:overview`, `resource:sklearn:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `resource:mit_algorithms:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:ECE310:2026-2027:overview`, `resource:numpy:overview`, `resource:python:overview`, `uofa:CSC110:2026-2027:overview`, `resource:pytorch:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:ECE352:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE372A:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:ECE340A:2026-2027:overview`, `resource:pico:overview`

### digital-systems-resource

What does MIT 6.004 cover, and what preparation does its syllabus assume?

Candidate order:

`resource:cs50:overview`, `resource:pytorch:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `resource:pico:overview`, `career:embedded:overview`, `uofa:ECE425:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `career:ai_ml:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `uofa:ECE381A:2026-2027:overview`, `resource:numpy:overview`, `uofa:ECE201:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:ECE340A:2026-2027:overview`, `uofa:ECE310:2026-2027:overview`, `resource:mit_algorithms:overview`, `uofa:ECE311:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `resource:sklearn:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:CSC372:2026-2027:overview`, `uofa:ECE351C:2026-2027:overview`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `resource:python:overview`, `uofa:ECE352:2026-2027:overview`

### algorithms-resource

Can MIT 6.006 help me practice algorithms and analyze performance?

Candidate order:

`uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:CSC372:2026-2027:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:ECE311:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `resource:pytorch:overview`, `uofa:ECE351C:2026-2027:overview`, `resource:pico:overview`, `uofa:CSC144:2026-2027:overview`, `career:embedded:overview`, `uofa:ECE372A:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `resource:sklearn:overview`, `resource:numpy:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE310:2026-2027:overview`, `resource:python:overview`, `uofa:ECE201:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `uofa:ECE369A:2026-2027:overview`, `uofa:CSC120:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:ECE220:2026-2027:overview`, `career:ai_ml:overview`, `uofa:CSC110:2026-2027:overview`, `resource:mit_structures:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:CSC210:2026-2027:rule:R1299-L70`, `resource:mit_algorithms:overview`, `uofa:ECE274A:2026-2027:overview`

### enrollment-limits

Can this collection confirm my exact graduation semester and guarantee enrollment?

Candidate order:

`uofa:CSC210:2026-2027:rule:R1299-L70`, `uofa:ECE310:2026-2027:overview`, `career:embedded:overview`, `uofa:ECE373:2026-2027:overview`, `uofa:ECE274A:2026-2027:overview`, `uofa:CSC144:2026-2027:rule:R1299-L50`, `uofa:CSC120:2026-2027:rule:R1299-L40`, `uofa:ECE351C:2026-2027:overview`, `uofa:ECE340A:2026-2027:overview`, `uofa:CSC144:2026-2027:overview`, `resource:mit_structures:overview`, `resource:python:overview`, `resource:sklearn:overview`, `uofa:CSC120:2026-2027:overview`, `uofa:CSC110:2026-2027:rule:R1299-L30`, `resource:numpy:overview`, `uofa:CSC110:2026-2027:overview`, `uofa:ECE320A:2026-2027:overview`, `uofa:ECE372A:2026-2027:overview`, `uofa:ECE101:2026-2027:overview`, `uofa:ECE352:2026-2027:overview`, `uofa:CSC210:2026-2027:overview`, `uofa:ECE201:2026-2027:overview`, `uofa:ECE425:2026-2027:overview`, `resource:mit_algorithms:overview`, `career:ai_ml:overview`, `uofa:CSC372:2026-2027:overview`, `resource:cs50:overview`, `uofa:ECE369A:2026-2027:overview`, `uofa:ECE220:2026-2027:overview`, `resource:pico:overview`, `resource:pytorch:overview`, `uofa:ECE381A:2026-2027:overview`, `uofa:ECE311:2026-2027:overview`

## Saved evidence

### uofa:ECE101:2026-2027:overview

ECE101: Programming 1
Introduces C programming, control flow, software design, memory management, and elementary data structures. Provides a foundation for further programming study.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 019404.
Team learning suggestion (not an academic requirement): Programming foundations support both directions. Use this to build confidence with C, control flow, and memory before more specialized study.

Sources:

- catalog:ECE101: ECE101 — Programming 1 — https://catalog.arizona.edu/courses/0432351 (snapshot retrieved 2026-10-23T04:05:07.731334+00:00)

### uofa:ECE369A:2026-2027:overview

ECE369A: Fundamentals of Computer Organization
Examines processor organization, instruction sets, memory and caches, and computer-design trade-offs. Uses MIPS and reduced-instruction-set examples to connect software with hardware behavior.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016494.
Team learning suggestion (not an academic requirement): Understanding processor instructions, memory, and caches provides a bridge from programming to embedded hardware.

Sources:

- catalog:ECE369A: ECE369A — Fundamentals of Computer Organization — https://catalog.arizona.edu/courses/0366021 (snapshot retrieved 2026-10-23T04:05:12.568170+00:00)

### uofa:ECE372A:2026-2027:overview

ECE372A: Microprocessor Organization
Studies microcontrollers and hardware interfaces through C programming, interrupts, timers, serial communication, and analog conversion. Includes laboratories and a project using a microcontroller platform.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016495.
Team learning suggestion (not an academic requirement): Microcontroller programming and hardware interfaces connect an embedded-systems goal with practical device projects. Prepare programming and processor foundations first.

Sources:

- catalog:ECE372A: ECE372A — Microprocessor Organization — https://catalog.arizona.edu/courses/0367521 (snapshot retrieved 2026-10-23T04:05:16.945042+00:00)

### uofa:ECE425:2026-2027:overview

ECE425: Introduction to Deep Learning: An Engineering Perspective
Introduces neural-network principles, optimization, and engineering applications. Covers perceptrons, convolutional and attention models, and methods for efficient model training and inference.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 019593.
Team learning suggestion (not an academic requirement): Neural-network principles and engineering applications connect to an AI/ML goal. Treat this as a later goal until the relevant academic preparation and enrollment requirements are confirmed.

Sources:

- catalog:ECE425: ECE425 — Introduction to Deep Learning: An Engineering Perspective — https://catalog.arizona.edu/courses/0435981 (snapshot retrieved 2026-10-23T04:05:20.982642+00:00)

### uofa:CSC120:2026-2027:overview

CSC120: Introduction to Computer Programming II
Develops programming and problem-solving skills through data structures and their implementations. Topics include lists, stacks, queues, trees, searching, sorting, and exceptions.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Use the separate prerequisite-source evidence and application rule results. Enrollment requirement reference: 017083.
Team learning suggestion (not an academic requirement): Data structures connect introductory programming with the software skills used in later AI work. Check the recorded grade requirement before considering enrollment.

Sources:

- catalog:CSC120: CSC120 — Introduction to Computer Programming II — https://catalog.arizona.edu/courses/0393701 (snapshot retrieved 2026-10-23T04:05:24.472577+00:00)

### uofa:CSC120:2026-2027:rule:R1299-L40

Prerequisite source statement for CSC120. Catalog: 2026-2027. Program: COSCBS. Section: R1299/L40.
Complete 1 course. C or better is required in CSC 110, ECE 101, ECE 175, or ISTA 130 prior to taking CSC 120.
Use only the application rule results to assess recorded prerequisite satisfaction. A source statement alone does not establish enrollment eligibility.

Sources:

- catalog:CS_foundations: Computer Science BS — foundation course requirements — https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj (snapshot retrieved 2026-11-04T04:02:39.295788+00:00)

### resource:pytorch:overview

resource:pytorch: PyTorch Quickstart
Practice a basic deep learning workflow with data loading, neural-network construction, optimization, and saved model parameters. A useful hands-on companion to introductory neural-network coursework.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Use this to connect Python programming with a small deep learning workflow after building programming foundations.
Suggested first activity: Work through loading data and running the example model. Note how the training and evaluation steps differ.

Sources:

- resource:pytorch: PyTorch Quickstart — https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html (snapshot retrieved 2026-10-23T04:01:51.068000+00:00)

### resource:cs50:overview

resource:cs50: CS50 — Introduction to Computer Science
Build programming foundations through C, algorithms, memory, and data structures, then progress to Python and web topics. OpenCourseWare provides material for independent study.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Use this alongside programming foundations when you want guided practice outside university coursework.
Suggested first activity: Start with the introduction and its first exercise. Move through the material at your own pace.

Sources:

- resource:cs50: CS50's Introduction to Computer Science — https://cs50.harvard.edu/x/ (snapshot retrieved 2026-10-23T04:01:51.068000+00:00)

### career:ai_ml:overview

career:ai_ml: AI and machine learning
Team learning connection: neural-network coursework and practical PyTorch exercises can support an interest in AI and machine learning. Programming and data-structure foundations provide supporting skills. This is a suggested learning direction, not a hiring or degree guarantee.
This is a team-authored learning connection, not a university requirement.

Sources:

- catalog:ECE425: ECE425 — Introduction to Deep Learning: An Engineering Perspective — https://catalog.arizona.edu/courses/0435981 (snapshot retrieved 2026-10-23T04:05:20.982642+00:00)
- catalog:CSC120: CSC120 — Introduction to Computer Programming II — https://catalog.arizona.edu/courses/0393701 (snapshot retrieved 2026-10-23T04:05:24.472577+00:00)
- resource:pytorch: PyTorch Quickstart — https://docs.pytorch.org/tutorials/beginner/basics/quickstart_tutorial.html (snapshot retrieved 2026-10-23T04:01:51.068000+00:00)

### career:embedded:overview

career:embedded: Embedded systems
Team learning connection: C programming, processor architecture, microcontrollers, and hardware interfaces form a useful learning direction for embedded systems. A course match indicates relevant study rather than proven job eligibility.
This is a team-authored learning connection, not a university requirement.

Sources:

- catalog:ECE101: ECE101 — Programming 1 — https://catalog.arizona.edu/courses/0432351 (snapshot retrieved 2026-10-23T04:05:07.731334+00:00)
- catalog:ECE369A: ECE369A — Fundamentals of Computer Organization — https://catalog.arizona.edu/courses/0366021 (snapshot retrieved 2026-10-23T04:05:12.568170+00:00)
- catalog:ECE372A: ECE372A — Microprocessor Organization — https://catalog.arizona.edu/courses/0367521 (snapshot retrieved 2026-10-23T04:05:16.945042+00:00)

### uofa:CSC110:2026-2027:overview

CSC110: Introduction to Computer Programming I
Programming fundamentals through problem solving, basic control and data structures, and development tools.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Use the separate prerequisite-source evidence and application rule results. Enrollment requirement reference: 017080.
Team learning suggestion (not an academic requirement): Use this as an introductory programming option; confirm program applicability and enrollment separately.
Suggested first activity: Write and test a small program that processes a list of measurements.

Sources:

- catalog:CSC110: CSC110 — Introduction to Computer Programming I — https://catalog.arizona.edu/courses/0393681 (snapshot retrieved 2026-11-06T17:59:18.692742+00:00)

### uofa:CSC110:2026-2027:rule:R1299-L30

Prerequisite source statement for CSC110. Catalog: 2026-2027. Program: COSCBS. Section: R1299/L30.
Complete 1 course. Appropriate math placement score or C or better in MATH 112 required prior to taking CSC 110. Only one course from CSC 110, ECE 101, ECE 175, and ISTA 130 may be used towards the program.
Use only the application rule results to assess recorded prerequisite satisfaction. A source statement alone does not establish enrollment eligibility.

Sources:

- catalog:CS_foundations: Computer Science BS — foundation course requirements — https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj (snapshot retrieved 2026-11-04T04:02:39.295788+00:00)

### uofa:CSC144:2026-2027:overview

CSC144: Discrete Mathematics for Computer Science I
Introduces discrete mathematics for computing, including logical statements, proofs, sets, relations, matrices, functions, and modular arithmetic.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Use the separate prerequisite-source evidence and application rule results. Enrollment requirement reference: 018647.
Team learning suggestion (not an academic requirement): Practice discrete reasoning alongside programming; this annotation does not replace the reviewed mathematics and programming conditions.
Suggested first activity: Translate a simple program condition into a logical statement and check a truth table.

Sources:

- catalog:CSC144: CSC144 — Discrete Mathematics for Computer Science I — https://catalog.arizona.edu/courses/0420001 (snapshot retrieved 2026-11-06T17:59:18.129831+00:00)

### uofa:CSC144:2026-2027:rule:R1299-L50

Prerequisite source statement for CSC144. Catalog: 2026-2027. Program: COSCBS. Section: R1299/L50.
Complete 1 course. C or higher in CSC 110 (or ECE 101 or ECE 175 or ISTA 130) and [appropriate math placement or (C or higher in MATH 112) or one course from MATH 113, 116, 120R, 122A, 122B, or 125], prior to taking CSC 144. Only one course from CSC 144, MATH 243 and MATH 323 may be used towards the program.
Use only the application rule results to assess recorded prerequisite satisfaction. A source statement alone does not establish enrollment eligibility.

Sources:

- catalog:CS_foundations: Computer Science BS — foundation course requirements — https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj (snapshot retrieved 2026-11-04T04:02:39.295788+00:00)

### uofa:CSC210:2026-2027:overview

CSC210: Software Development
Developing larger software systems with modular design, patterns, documentation, unit tests, version control, build tools, debugging, and performance analysis.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Use the separate prerequisite-source evidence and application rule results. Enrollment requirement reference: 017084.
Team learning suggestion (not an academic requirement): Build on programming experience by organizing and testing a project with several modules.
Suggested first activity: Split a small program into modules and add a repeatable unit test.

Sources:

- catalog:CSC210: CSC210 — Software Development — https://catalog.arizona.edu/courses/0393711 (snapshot retrieved 2026-11-06T17:59:18.343903+00:00)

### uofa:CSC210:2026-2027:rule:R1299-L70

Prerequisite source statement for CSC210. Catalog: 2026-2027. Program: COSCBS. Section: R1299/L70.
Complete 1 course. C or better is required in CSC 120 prior to taking CSC 210.
Use only the application rule results to assess recorded prerequisite satisfaction. A source statement alone does not establish enrollment eligibility.

Sources:

- catalog:CS_foundations: Computer Science BS — foundation course requirements — https://catalog.arizona.edu/programs/COSCBS/program-requirements-a1nCj (snapshot retrieved 2026-11-04T04:02:39.295788+00:00)

### uofa:ECE201:2026-2027:overview

ECE201: Programming 2
C++ programming with classes and data abstraction, inheritance and polymorphism, exceptions, linked structures, and the complexity of searching, sorting, and traversal algorithms.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 019415.
Team learning suggestion (not an academic requirement): Connect introductory programming to data structures and C++ abstractions; foundation is a preparation label, not first-course eligibility.
Suggested first activity: Implement a small stack class and test its empty and nonempty cases.

Sources:

- catalog:ECE201: ECE201 — Programming 2 — https://catalog.arizona.edu/courses/0432591 (snapshot retrieved 2026-11-06T17:59:24.075135+00:00)

### uofa:ECE220:2026-2027:overview

ECE220: Basic Circuits
Circuit analysis with laboratory work, covering node and mesh methods, equivalent circuits, operational amplifiers, transient responses, sinusoidal signals, impedance, and simulation.
Credits: 5.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016467.
Team learning suggestion (not an academic requirement): Develop circuit-analysis skills before exploring more specialized electronics.
Suggested first activity: Solve a small resistor network with node equations and compare the result with a simulation.

Sources:

- catalog:ECE220: ECE220 — Basic Circuits — https://catalog.arizona.edu/courses/0120881 (snapshot retrieved 2026-11-06T17:59:24.072438+00:00)

### uofa:ECE274A:2026-2027:overview

ECE274A: Digital Logic
Covers number representations, coding, combinational logic design, sequential systems, and register-transfer descriptions.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016468.
Team learning suggestion (not an academic requirement): Use logic design to connect programming ideas with digital hardware.
Suggested first activity: Draw and check a truth table for a small combinational circuit.

Sources:

- catalog:ECE274A: ECE274A — Digital Logic — https://catalog.arizona.edu/courses/0360981 (snapshot retrieved 2026-11-06T17:59:23.927280+00:00)

### uofa:ECE310:2026-2027:overview

ECE310: Applications of Engineering Mathematics
Engineering mathematics covering linear systems, vector spaces, eigenvalues, probability distributions, estimation, and confidence intervals, with MATLAB projects.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016491.
Team learning suggestion (not an academic requirement): Use mathematics exercises to support later work in signals, hardware, and machine learning.
Suggested first activity: Compute a matrix projection and summarize the mean and variance of a small dataset.

Sources:

- catalog:ECE310: ECE310 — Applications of Engineering Mathematics — https://catalog.arizona.edu/courses/0362401 (snapshot retrieved 2026-11-06T17:59:29.708836+00:00)

### uofa:ECE311:2026-2027:overview

ECE311: Engineering Ethics and Contemporary Issues
Introduces professional engineering ethics and contemporary questions about the effects of technology and engineered systems on everyday life.
Credits: 1.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 017368.
Team learning suggestion (not an academic requirement): Include ethical reasoning when discussing a technical design. The unresolved requirement reference remains separate from descriptive prerequisite wording.
Suggested first activity: Compare two design choices by identifying stakeholders, possible harms, and tradeoffs.

Sources:

- catalog:ECE311: ECE311 — Engineering Ethics and Contemporary Issues — https://catalog.arizona.edu/courses/0397381 (snapshot retrieved 2026-11-06T17:59:29.771042+00:00)

### uofa:ECE320A:2026-2027:overview

ECE320A: Circuit Theory
Analyzes circuits using frequency-domain techniques, Laplace and Fourier methods, convolution, power systems, transformed networks, poles and zeros, and two-port parameters.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016492.
Team learning suggestion (not an academic requirement): Connect time-domain circuit behavior with transforms and frequency responses.
Suggested first activity: Sketch the poles and frequency response of a simple RC circuit.

Sources:

- catalog:ECE320A: ECE320A — Circuit Theory — https://catalog.arizona.edu/courses/0121101 (snapshot retrieved 2026-11-06T17:59:29.880125+00:00)

### uofa:ECE340A:2026-2027:overview

ECE340A: Introduction to Communications
Communication-system analysis and design using Fourier methods, filtering and spectra, analog and digital modulation, quantization, line coding, and transmitter/receiver concepts.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016474.
Team learning suggestion (not an academic requirement): Explore how signal representations and modulation choices affect a communication link.
Suggested first activity: Compare a message signal with a simple amplitude-modulated waveform.

Sources:

- catalog:ECE340A: ECE340A — Introduction to Communications — https://catalog.arizona.edu/courses/0377871 (snapshot retrieved 2026-11-06T17:59:34.985632+00:00)

### uofa:ECE351C:2026-2027:overview

ECE351C: Electronic Circuits
Studies diodes, bipolar and MOS transistors, operational amplifiers, small-signal amplifier models, digital circuit elements, and circuit simulation.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016474.
Team learning suggestion (not an academic requirement): Move from linear circuit exercises toward device models and amplifier design.
Suggested first activity: Compare a transistor operating point with its small-signal approximation.

Sources:

- catalog:ECE351C: ECE351C — Electronic Circuits — https://catalog.arizona.edu/courses/0366011 (snapshot retrieved 2026-11-06T17:59:34.413377+00:00)

### uofa:ECE373:2026-2027:overview

ECE373: Object-Oriented Software Design
Object-oriented design and implementation using classes, inheritance, polymorphism, abstract data types, design architectures, use cases, sequence diagrams, and UML.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016496.
Team learning suggestion (not an academic requirement): Use software modeling to explain the structure of a larger implementation.
Suggested first activity: Draw a class diagram for a small device controller and implement one class.

Sources:

- catalog:ECE373: ECE373 — Object-Oriented Software Design — https://catalog.arizona.edu/courses/0121261 (snapshot retrieved 2026-11-06T17:59:34.913497+00:00)

### resource:python:overview

resource:python: The Python Tutorial
Official Python language tutorial covering core programming concepts, data structures, modules, and classes. It is written for readers with basic programming knowledge who are new to Python.
Resource edition/version: 3.15.2.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Practice Python after learning general programming basics; this tutorial expects some programming experience.
Suggested first activity: Run a short Python script that reads numbers into a list and computes a summary.

Sources:

- resource:python: The Python Tutorial — https://docs.python.org/3/tutorial/index.html (snapshot retrieved 2026-11-06T17:55:03.324334+00:00)

### resource:numpy:overview

resource:numpy: NumPy quickstart
Official NumPy quickstart for numerical arrays. Its introductory prerequisites call for some Python knowledge and matplotlib for the examples.
Resource edition/version: 2.5.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Use arrays to connect mathematical exercises with Python numerical code after basic Python practice.
Suggested first activity: Create a small array and compare element-wise multiplication with matrix multiplication.

Sources:

- resource:numpy: NumPy quickstart — https://numpy.org/doc/stable/user/quickstart.html (snapshot retrieved 2026-11-06T17:55:07.123770+00:00)

### resource:sklearn:overview

resource:sklearn: scikit-learn Getting Started
Official introduction to scikit-learn workflows for fitting models, preprocessing data, choosing models, and evaluating predictions. The guide assumes basic familiarity with machine-learning practice.
Resource edition/version: 1.9.1.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Practice a simple measured learning workflow after studying basic machine-learning concepts.
Suggested first activity: Fit a small example classifier and explain why evaluation uses data separate from fitting.

Sources:

- resource:sklearn: scikit-learn Getting Started — https://scikit-learn.org/stable/getting_started.html (snapshot retrieved 2026-11-06T17:55:07.912673+00:00)

### resource:pico:overview

resource:pico: Raspberry Pi Pico C/C++ SDK
Official Raspberry Pi Pico C/C++ SDK guide describing development tools, example projects, SDK documentation, and initial programs for a microcontroller board.
Resource edition/version: unversioned documentation.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Use a small microcontroller project to connect C/C++ programming with device behavior; hardware and toolchain setup are separate practical requirements.
Suggested first activity: Read the board-specific setup instructions and trace the supplied LED blink example before adapting it.

Sources:

- resource:pico: Raspberry Pi Pico C/C++ SDK — https://www.raspberrypi.com/documentation/microcontrollers/c_sdk.html (snapshot retrieved 2026-11-06T17:55:07.656760+00:00)

### uofa:ECE352:2026-2027:overview

ECE352: Device Electronics
Examines semiconductor electronic properties, charge-carrier transport, junction behavior, and several classes of electronic, microwave, and photonic devices.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016472.
Team learning suggestion (not an academic requirement): Connect circuit models with semiconductor-device behavior; the preparation label does not resolve enrollment conditions.
Suggested first activity: Sketch a qualitative junction diagram and explain the direction of charge-carrier motion.

Sources:

- catalog:ECE352: ECE352 — Device Electronics — https://catalog.arizona.edu/courses/0121181 (snapshot retrieved 2026-11-06T18:37:35.201440+00:00)

### uofa:ECE381A:2026-2027:overview

ECE381A: Introductory Electromagnetics
Introduces electric and magnetic fields, Maxwell equations, wave propagation, transmission lines, and electromagnetic sources.
Credits: 4.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 016497.
Team learning suggestion (not an academic requirement): Connect circuit and signal exercises with field and wave descriptions before more specialized hardware study.
Suggested first activity: Compare the assumptions of a lumped circuit model with a transmission-line model.

Sources:

- catalog:ECE381A: ECE381A — Introductory Electromagnetics — https://catalog.arizona.edu/courses/0375981 (snapshot retrieved 2026-11-06T18:37:34.703180+00:00)

### uofa:CSC372:2026-2027:overview

CSC372: Comparative Programming Languages
Compares several high-level programming languages and their characteristics, with programming projects using at least three languages.
Credits: 3.0. Catalog: 2026-2027.
Academic rule: Unresolved. Do not infer enrollment eligibility. Enrollment requirement reference: 017273.
Team learning suggestion (not an academic requirement): Compare language choices and express the same idea in different programming styles; this is a learning connection, not a prerequisite interpretation.
Suggested first activity: Implement a small data-processing task in two languages and compare their type and control-flow conventions.

Sources:

- catalog:CSC372: CSC372 — Comparative Programming Languages — https://catalog.arizona.edu/courses/0098011 (snapshot retrieved 2026-11-06T18:37:40.264676+00:00)

### resource:mit_algorithms:overview

resource:mit_algorithms: MIT 6.006 — Introduction to Algorithms
Archived MIT algorithms course covering data structures, problem modeling, algorithmic techniques, and computational performance analysis.
Resource edition/version: Spring 2020.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Archived Spring 2020 material expects Python programming and discrete mathematics. Use it for complementary practice, not university credit or course equivalency.
Suggested first activity: Trace a small sorting algorithm and compare its operation count with a second approach.

Sources:

- resource:mit_algorithms: MIT 6.006 — Introduction to Algorithms — https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/pages/syllabus/ (snapshot retrieved 2026-11-06T18:36:36.957974+00:00)

### resource:mit_structures:overview

resource:mit_structures: MIT 6.004 — Computation Structures
Archived MIT digital-systems course connecting transistor-level behavior to logic, sequential circuits, state machines, and computers through hardware/software design examples.
Resource edition/version: Spring 2017.
Complementary learning resource; this does not establish university credit or course equivalency.
Team learning suggestion (not an academic requirement): Archived Spring 2017 material assumes programming concepts and electrical fundamentals; review its syllabus preparation before using the exercises.
Suggested first activity: Trace how a logic circuit stores state and relate it to a small processor building block.

Sources:

- resource:mit_structures: MIT 6.004 — Computation Structures — https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/pages/syllabus/ (snapshot retrieved 2026-11-06T18:36:36.954953+00:00)
