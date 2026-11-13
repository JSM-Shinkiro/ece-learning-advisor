"""Self-guided lessons and the local retrieval lab."""

import inspect
import json
from dataclasses import asdict

import numpy as np
import streamlit as st

from .catalog import ROOT, corpus_hash
from .inspection_views import ranking_html
from .learning_lab import (
    PRESETS, TOPICS, build_lab_index, compare_ranks, evidence_fit, keyword_terms,
    matched_topic_terms, plot_experiment, run_experiment, topic_vector,
)
from .retrieval import project_embeddings, reciprocal_rank_fusion, tokenize

LEARNING_ASSETS = ROOT / "assets/learning"
LESSONS = ("Beginner", "Intermediate", "Advanced")
METHODS = {"keyword": "Keyword", "semantic": "Topic cosine", "hybrid": "Hybrid"}
RANK_CHANGES = ("Moved up", "Moved down", "Stayed at the same rank", "Entered the ranking", "Left the ranking")


def show_section(section):
    st.session_state.view = section


def _finish(stage):
    st.session_state["lesson_" + stage.lower()] = True


def _roadmap():
    st.subheader("Learning roadmap")
    goals = (
        (":material/school:", "Remember & understand", "Explain how a question leads to source-backed evidence."),
        (":material/tune:", "Apply & analyze", "Compare rankings for a preset question."),
        (":material/construction:", "Evaluate & create", "Build and evaluate your own variation."),
    )
    for column, stage, (icon, actions, goal) in zip(st.columns(3), LESSONS, goals):
        with column, st.container(border=True):
            st.markdown(f"**{icon} {stage}**")
            st.caption(actions)
            st.write(goal)
            label = "Review lesson" if st.session_state.get("lesson_" + stage.lower()) else "Open " + stage.lower()
            st.button(label, key="learn_go_" + stage.lower(), width="stretch", on_click=show_section, args=(stage,))


def render_beginner():
    copy, visual = st.columns([3, 2], vertical_alignment="center")
    with copy:
        st.title("Learn how an ECE advisor finds evidence")
        st.write("Explore how a question about electrical and computer engineering turns into course and resource suggestions you can inspect.")
        st.markdown("**:material/memory: Embedded systems** connect software to sensors, processors and devices.\n\n"
                    "**:material/hub: AI and machine learning** use data and models to recognize patterns or make predictions.")
        st.write("Together these skills help build robots, connected devices and systems that interpret images or signals.")
        st.caption("For prospective and current ECE students. Start with an interest such as robotics, programming or computer vision.")
        st.button("Try a preset experiment", type="primary", on_click=show_section, args=("Intermediate",))
    with visual:
        st.image(LEARNING_ASSETS / "ece-lab.webp", width="stretch", caption="Electronics lab illustration")

    _roadmap()

    st.subheader("From interest to evidence")
    st.html("""<style>
    .ece-flow {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1rem;padding:0;margin:0;list-style:none}
    .ece-flow li {position:relative;background:#131e31;border:1px solid #334861;border-radius:.65rem;padding:.85rem;min-width:0}
    .ece-flow li:not(:last-child)::after {content:'→';position:absolute;right:-.84rem;top:35%;color:#78b8ff}
    .ece-flow strong {display:block;color:#b7dbff;margin-bottom:.3rem}
    .ece-flow span {color:#d3dfef;font-size:.92rem}
    @media(max-width:720px) {.ece-flow{grid-template-columns:1fr;gap:.75rem}.ece-flow li:not(:last-child)::after {content:'↓';top:auto;bottom:-.8rem;right:50%}}
    </style>
    <ol class="ece-flow" aria-label="Question to evidence flowchart">
      <li><strong>Ask a question</strong><span>Enter an interest and your preparation.</span></li>
      <li><strong>Rank evidence</strong><span>Match the question to saved descriptions.</span></li>
      <li><strong>Check preparation</strong><span>Review your courses and known requirements.</span></li>
      <li><strong>Inspect a plan</strong><span>Open the sources and see why a result appeared.</span></li>
    </ol>""")

    st.subheader("Know these before you start")
    for column, label, body in zip(st.columns(3),
        ("Search", "Vectors", "Prerequisites"),
        ("Keyword search finds shared words. Similarity search compares numerical descriptions of meaning.",
         "A vector represents a question as numbers. In this lesson, “sensors and Python” adds one "
         "count to Embedded hardware and one to Programming.",
         "Your completed courses and catalog year affect preparation checks. Confirm enrollment on the official course page.")):
        with column:
            st.markdown(f"**{label}**")
            st.write(body)
    st.caption("Retrieval-augmented generation (RAG) gives a language model selected sources so it can explain a suggestion using evidence.")
    st.caption("Use the catalog year that applies to you. You can leave course history blank and practice with the built-in examples.")
    answer = st.radio("What tells you whether you meet a course’s prerequisites?",
                      ("The ranking score", "The official requirements and my completed coursework"),
                      index=None, key="learn_foundations_answer")
    if answer:
        if answer.startswith("The official"):
            _finish("Beginner")
            st.success("Correct. A relevance score helps you find a course. Its source and your coursework help you check preparation.")
        else:
            st.info("Check the course’s requirements and your coursework. A highly relevant course may require more preparation.")


def _render_experiment(index, experiment, chart_key):
    chart_column, ranking_column = st.columns([3, 2])
    with chart_column:
        st.plotly_chart(plot_experiment(index, experiment), key=chart_key, width="stretch",
                        config={"displayModeBar": False})
        st.caption("The star marks the question when it matches a topic. Teal marks the top three records. "
                   "PCA draws the four topic counts on two axes. Cosine uses all four counts.")
    with ranking_column:
        labels = {doc.record_id: label for label, doc in zip(index.labels, index.retriever.evidence)}
        rows = [(labels[hit.record_id], hit.score) for hit in experiment.hits[:5]]
        st.html(ranking_html(rows, METHODS[experiment.method]))
        st.caption("Compare positions within a method. The methods use different score scales.")


def _developer_view(index, experiment, key):
    panel = st.expander("Developer view · visualization code", key=key, on_change="rerun")
    if not panel.open:
        return
    labels = {doc.record_id: label for label, doc in zip(index.labels, index.retriever.evidence)}
    with panel:
        st.caption("The lab counts listed terms in four topics. The advisor can use Gemini embeddings when configured.")
        st.json(TOPICS, expanded=False)
        st.dataframe([{"Record": "Question", **dict(zip(TOPICS, experiment.vector))}] + [
            {"Record": label, **dict(zip(TOPICS, vector))} for label, vector in zip(index.labels, index.vectors)
        ], hide_index=True, width="stretch")
        st.dataframe([{"Record": labels[hit.record_id], "Score": hit.score, "BM25": hit.keyword_score,
                       "Cosine": hit.cosine_score} for hit in experiment.hits], hide_index=True, width="stretch")
        st.code(inspect.getsource(topic_vector) + "\n\n" + inspect.getsource(project_embeddings) + "\n\n" +
                inspect.getsource(plot_experiment), language="python", line_numbers=True)
        if experiment.method == "hybrid":
            st.code(inspect.getsource(reciprocal_rank_fusion), language="python", line_numbers=True)


def _show_evidence(index, experiment, record_id):
    document = next(doc for doc in index.retriever.evidence if doc.record_id == record_id)
    if experiment.method != "semantic":
        words = sorted(keyword_terms(experiment.query) & set(tokenize(document.text)))
        st.caption("Shared search words · " + (", ".join(words) or "none"))
    if experiment.method != "keyword":
        counts = topic_vector(document.text)
        dot = float(np.dot(experiment.vector, counts))
        lengths = float(np.linalg.norm(experiment.vector) * np.linalg.norm(counts))
        st.caption(f"Topic cosine · {dot:g} dot product ÷ {lengths:.3f} product of lengths = {dot / lengths:.3f}")
        matches = [term for terms in matched_topic_terms(document.text).values() for term in terms]
        st.table([{"Topic": topic, "Question": int(question_count), "Record": int(record_count)}
                  for topic, question_count, record_count in zip(TOPICS, experiment.vector, counts)])
        st.caption("Record topic words · " + ", ".join(matches))
    st.write(document.text)
    for source in index.catalog.sources:
        if source.source_id in document.source_ids:
            st.link_button(source.title, source.url)


@st.fragment
def render_intermediate(index):
    st.title("Intermediate · Apply & analyze")
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.write("Choose a preset. Compare how shared words and topic similarity order the same evidence.")
        preset = st.selectbox("Preset question", list(PRESETS), key="learn_preset", persist_state="session")
        query = PRESETS[preset]
        st.markdown(f"**{query}**")
        method = st.selectbox("Ranking method", list(METHODS), format_func=METHODS.get,
                              key="learn_method", persist_state="session")
        st.caption({
            "keyword": "BM25 weighs matching terms by how often they appear in the collection.",
            "semantic": "Cosine compares the direction of all four topic counts for the question and each record.",
            "hybrid": "Hybrid combines positions from the keyword and cosine rankings.",
        }[method])
    with right:
        st.image(LEARNING_ASSETS / "retrieval-lab.webp", width="stretch", caption="Illustration of a retrieval workspace")
    experiment = run_experiment(index, query, method)
    _render_experiment(index, experiment, "lesson_preset_plot")
    labels = {doc.record_id: label for doc, label in zip(index.retriever.evidence, index.labels)}
    evidence_panel = st.expander("Inspect evidence", key="lesson_preset_evidence", on_change="rerun")
    if evidence_panel.open:
        with evidence_panel:
            record_id = st.selectbox("Evidence record", [hit.record_id for hit in experiment.hits],
                                     format_func=labels.get, key="lesson_preset_record")
            _show_evidence(index, experiment, record_id)
    _developer_view(index, experiment, "lesson_preset_code")
    other = "semantic" if method == "keyword" else "keyword"
    reference = run_experiment(index, query, other)
    before = {hit.record_id for hit in reference.hits[:3]}
    after = {hit.record_id for hit in experiment.hits[:3]}
    changed_records = before ^ after
    moved = [label for label, doc in zip(index.labels, index.retriever.evidence) if doc.record_id in changed_records]
    if moved:
        st.caption(f"Compared with {METHODS[other]}, the top three change for {', '.join(moved)}.")
    else:
        st.caption(f"The top three contain the same records as {METHODS[other]}. Check their order and scores.")
    first = st.selectbox("Which record ranks first with these settings?", list(labels), index=None,
                         format_func=labels.get, key="learn_rank_answer")
    if first == experiment.hits[0].record_id:
        _finish("Intermediate")
        st.success("Correct. Switch methods and check which records move.")
    elif first:
        st.info("Look at the first bar in the ranking and try again.")
    if st.button("Create your variation", type="primary", help="Use this preset and ranking method in Advanced."):
        st.session_state.learn_baseline = preset
        st.session_state.learn_variant_method = method
        st.session_state.lesson_destination = "Advanced"
        st.rerun()


def _rank_change(before, after):
    if before is None:
        return "Entered the ranking"
    if after is None:
        return "Left the ranking"
    if before == after:
        return "Stayed at the same rank"
    return "Moved up" if after < before else "Moved down"


def _review_comparison(index, baseline, variation, rows, labels):
    st.subheader("Explain a result")
    ranks = {row["Record"]: (row["Preset rank"], row["Your rank"]) for row in rows}
    record_id = st.selectbox("Record to explain", list(ranks), index=None, format_func=labels.get,
                             key="learn_observation_record", persist_state="session")
    if record_id is None:
        return

    before, after = ranks[record_id]
    st.caption(f"Preset rank · {before or 'outside the ranking'}   |   Your rank · {after or 'outside the ranking'}")
    with st.expander("Inspect evidence for this record"):
        _show_evidence(index, variation if after is not None else baseline, record_id)
    movement = st.selectbox("How did this record move?", RANK_CHANGES, index=None,
                            key="learn_observation_movement", persist_state="session")
    observation = st.text_area("What in the evidence explains the result?", max_chars=600,
                               key="learn_observation", persist_state="session")
    if st.button("Save my observation"):
        if movement is None:
            st.info("Choose how the record moved before saving your explanation.")
        elif movement != _rank_change(before, after):
            st.warning("Check the two ranks above and try the rank change again.")
        elif len(keyword_terms(observation)) < 2:
            st.warning("Write a short explanation that refers to a detail in the evidence.")
        else:
            st.session_state.learn_saved_reflection = {
                "record_id": record_id, "rank_change": movement, "explanation": observation.strip(),
            }
            _finish("Advanced")
            st.success("Rank change confirmed. Your explanation is saved.")


@st.fragment
def render_advanced(index):
    state = st.session_state
    st.title("Advanced · Evaluate & create")
    st.write("Write your own question and compare it with a preset. Choose which records you expect to help before you run it.")
    labels = {doc.record_id: label for label, doc in zip(index.labels, index.retriever.evidence)}
    saved = state.get("learn_variation")
    if saved is not None:
        saved = (saved[0], saved[1], saved[2], tuple(saved[3]))
        state.setdefault("learn_baseline", saved[0])
        state.setdefault("learn_variant_method", saved[1])
        state.setdefault("learn_variation_query", saved[2])
        state.setdefault("learn_expected_records", list(saved[3]))
    else:
        state.setdefault("learn_baseline", state.get("learn_preset", next(iter(PRESETS))))
        state.setdefault("learn_variant_method", state.get("learn_method", "hybrid"))
    if "learn_saved_observation" in state:
        legacy_observation = state.pop("learn_saved_observation")
        state.setdefault("learn_observation", legacy_observation)
        state.pop("lesson_advanced", None)
    with st.container(border=True):
        left, right = st.columns(2)
        preset = left.selectbox("Comparison preset", list(PRESETS), key="learn_baseline", persist_state="session")
        method = right.selectbox("Variation ranking method", list(METHODS), format_func=METHODS.get,
                                 key="learn_variant_method", persist_state="session")
        query = st.text_input("Your variation", key="learn_variation_query", max_chars=280,
                              live="0ms", on_change="ignore",
                              placeholder="How can I program a microcontroller to read a sensor?",
                              persist_state="session")
        expected = st.multiselect("Expected useful records", list(labels), format_func=labels.get,
                                  key="learn_expected_records", max_selections=3, persist_state="session")
        submitted = st.button("Compare with preset", type="primary")
    draft = (preset, method, query.strip(), tuple(expected))
    comparison = None
    if submitted:
        if not query.strip() or not expected:
            st.error("Enter a question and choose at least one expected record.")
        else:
            try:
                comparison = run_experiment(index, draft[2], method)
            except ValueError as error:
                st.error(str(error))
            else:
                if draft != saved:
                    state.learn_variation = saved = draft
                    state.learn_observation_record = None
                    state.learn_observation_movement = None
                    state.learn_observation = ""
                    state.pop("learn_saved_reflection", None)
                    state.pop("lesson_advanced", None)
    if saved is None:
        return
    preset, method, query, expected = saved
    try:
        variation = comparison or run_experiment(index, query, method)
    except ValueError:
        st.info("Update your draft and run the comparison again to use the current lesson records.")
        return
    baseline = run_experiment(index, PRESETS[preset], variation.method)
    st.subheader("Your comparison")
    if draft != saved:
        st.info("Showing your last comparison. Select Compare with preset to apply your draft.")
    st.caption(f"{METHODS[variation.method]} · preset “{PRESETS[preset]}”")
    st.text(query)
    if variation.method != method:
        st.info("Your question has a shared keyword and zero topic counts. Both rankings use Keyword.")
    topics = [topic for topic, terms in matched_topic_terms(query).items() if terms]
    if topics:
        st.caption("Recognized topics · " + ", ".join(topics))
    for column, title, experiment in zip(st.columns(2), ("Preset", "Your variation"), (baseline, variation)):
        column.metric(title + " expected records in top 3", f"{evidence_fit(experiment, expected)} / {len(expected)}")
    rows = compare_ranks(baseline, variation)
    displayed_ranks = [dict(row, Record=labels[row["Record"]]) for row in rows]
    st.dataframe(displayed_ranks, hide_index=True, width="stretch")
    _render_experiment(index, variation, "lesson_variation_plot")
    _developer_view(index, variation, "lesson_variation_code")
    _review_comparison(index, baseline, variation, rows, labels)
    if reflection := state.get("learn_saved_reflection"):
        st.caption("Observation saved in this session. Download a copy to keep it.")
        export = {
            "schema_version": 1, "preset": preset, "preset_question": PRESETS[preset], "question": query,
            "method": variation.method, "requested_method": method,
            "representation": {"keyword": "keywords", "semantic": "topic_counts",
                               "hybrid": "keywords_and_topic_counts"}[variation.method],
            "catalog_hash": corpus_hash(index.catalog),
            "record_ids": list(labels),
            "expected_records": [labels[record] for record in expected], "expected_record_ids": list(expected),
            "ranks": displayed_ranks, "preset_hits": [asdict(hit) for hit in baseline.hits],
            "variation_hits": [asdict(hit) for hit in variation.hits],
            "observation": reflection["explanation"], "observation_record_id": reflection["record_id"],
            "observed_rank_change": reflection["rank_change"],
        }
        st.download_button("Download my comparison", json.dumps(export, indent=2),
                           file_name="ece-experiment.json", mime="application/json", on_click="ignore")
    if st.button("Use this question in Advisor"):
        state.lesson_advisor_question = query
        state.lesson_question_pending = True
        state.lesson_destination = "Advisor"
        st.rerun()


def render_lesson(view, catalog):
    if view == "Beginner":
        render_beginner()
        return
    index = build_lab_index(catalog.model_dump_json())
    if view == "Intermediate":
        render_intermediate(index)
    else:
        render_advanced(index)
