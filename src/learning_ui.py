"""Self-guided lessons and the local retrieval lab."""

import inspect
import json

import streamlit as st

from .catalog import ROOT
from .inspection_views import ranking_html
from .learning_lab import PRESETS, TOPICS, build_lab_index, compare_ranks, evidence_fit, plot_experiment, run_experiment, topic_vector
from .retrieval import project_embeddings, reciprocal_rank_fusion

LEARNING_ASSETS = ROOT / "assets/learning"
LESSONS = ("Beginner", "Intermediate", "Advanced")
METHODS = {"keyword": "Keyword", "semantic": "Topic cosine", "hybrid": "Hybrid"}


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
         "An embedding represents text as numbers. A plot can project those numbers onto two axes.",
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
    st.button("Try a preset experiment", type="primary", on_click=show_section, args=("Intermediate",))


def _render_experiment(index, experiment, chart_key):
    chart_column, ranking_column = st.columns([3, 2])
    with chart_column:
        st.plotly_chart(plot_experiment(index, experiment), key=chart_key, width="stretch",
                        config={"displayModeBar": False})
        st.caption("The star marks the question when it matches a topic. Teal marks the top three records. PCA shows the vectors on two axes.")
    with ranking_column:
        labels = {doc.record_id: label for label, doc in zip(index.labels, index.retriever.evidence)}
        rows = [(labels[hit.record_id], hit.score) for hit in experiment.hits[:5]]
        if rows:
            st.html(ranking_html(rows, METHODS[experiment.method]))
        else:
            st.info("No records share searchable keywords with this question.")
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
        if experiment.hits:
            evidence = {doc.record_id: doc for doc in index.retriever.evidence}
            record_id = st.selectbox("Inspect saved evidence", [hit.record_id for hit in experiment.hits],
                                     format_func=labels.get, key=key + "_evidence")
            st.write(evidence[record_id].text)
            source_ids = set(evidence[record_id].source_ids)
            for source in index.catalog.sources:
                if source.source_id in source_ids:
                    st.link_button(source.title, source.url)


@st.fragment
def render_intermediate(index):
    st.title("Intermediate · Apply & analyze")
    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
        st.write("Choose a preset. Compare how shared words and topic similarity order the same evidence.")
        preset = st.selectbox("Preset question", list(PRESETS), key="learn_preset")
        query = PRESETS[preset]
        st.markdown(f"**{query}**")
        method = st.selectbox("Ranking method", list(METHODS), format_func=METHODS.get, key="learn_method")
        st.caption({
            "keyword": "BM25 weighs matching terms by how often they appear in the collection.",
            "semantic": "Cosine compares the direction of all four topic counts for the question and each record.",
            "hybrid": "Hybrid combines positions from the keyword and cosine rankings.",
        }[method])
    with right:
        st.image(LEARNING_ASSETS / "retrieval-lab.webp", width="stretch", caption="Illustration of a retrieval workspace")
    experiment = run_experiment(index, query, method)
    _render_experiment(index, experiment, "lesson_preset_plot")
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
    if experiment.hits:
        choices = [doc.record_id for doc in index.retriever.evidence]
        labels = dict(zip(choices, index.labels))
        first = st.selectbox("Which record ranks first with these settings?", [None, *choices],
                             format_func=lambda value: labels.get(value, "Choose a record"), key="learn_rank_answer")
        if first == experiment.hits[0].record_id:
            _finish("Intermediate")
            st.success("Correct. Switch methods and check which records move.")
        elif first:
            st.info("Look at the first bar in the ranking and try again.")
    if st.button("Create your variation", type="primary"):
        st.session_state.lesson_destination = "Advanced"
        st.rerun()


@st.fragment
def render_advanced(index):
    st.title("Advanced · Evaluate & create")
    st.write("Write your own question and compare it with a preset. Choose which records you expect to help before you run it.")
    labels = {doc.record_id: label for label, doc in zip(index.labels, index.retriever.evidence)}
    with st.form("lesson_variation_form"):
        left, right = st.columns(2)
        preset = left.selectbox("Comparison preset", list(PRESETS), key="learn_baseline")
        method = right.selectbox("Variation ranking method", list(METHODS), index=2, format_func=METHODS.get,
                                 key="learn_variant_method")
        query = st.text_input("Your variation", key="learn_variation_query", max_chars=280,
                              placeholder="How can I program a microcontroller to read a sensor?")
        expected = st.multiselect("Expected useful records", list(labels), format_func=labels.get,
                                  key="learn_expected_records", max_selections=3)
        submitted = st.form_submit_button("Compare with preset", type="primary")
    if submitted:
        if not query.strip() or not expected:
            st.error("Enter a question and choose at least one expected record.")
        else:
            try:
                run_experiment(index, query.strip(), method)
            except ValueError as error:
                st.error(str(error))
            else:
                st.session_state.learn_variation = (preset, method, query.strip(), expected)
                st.session_state.pop("learn_observation", None)
                st.session_state.pop("learn_saved_observation", None)
    saved = st.session_state.get("learn_variation")
    if saved is None:
        return
    preset, method, query, expected = saved
    baseline = run_experiment(index, PRESETS[preset], method)
    variation = run_experiment(index, query, method)
    st.subheader("Your comparison")
    st.caption(f"{METHODS[method]} · preset “{PRESETS[preset]}”")
    st.text(query)
    for column, title, experiment in zip(st.columns(2), ("Preset", "Your variation"), (baseline, variation)):
        column.metric(title + " expected records in top 3", f"{evidence_fit(experiment, expected)} / {len(expected)}")
    rows = compare_ranks(baseline, variation)
    for row in rows:
        row["Record"] = labels[row["Record"]]
    st.dataframe(rows, hide_index=True, width="stretch")
    _render_experiment(index, variation, "lesson_variation_plot")
    _developer_view(index, variation, "lesson_variation_code")
    st.caption("Use the score table and evidence excerpts to explain a rank change. Your expected records are your own evaluation criteria.")
    observation = st.text_area("What moved, and what in the evidence explains it?", max_chars=600,
                               key="learn_observation", value=st.session_state.get("learn_saved_observation", ""))
    if st.button("Save my observation", disabled=not observation.strip()):
        st.session_state.learn_saved_observation = observation.strip()
        _finish("Advanced")
    if saved_observation := st.session_state.get("learn_saved_observation"):
        st.caption("Observation saved in this session. Download a copy to keep it.")
        st.download_button("Download my comparison", json.dumps({"preset": preset, "question": query, "method": method,
                           "expected_records": [labels[record] for record in expected], "ranks": rows,
                           "observation": saved_observation}, indent=2), file_name="ece-experiment.json",
                           mime="application/json", on_click="ignore")
    if st.button("Open the advisor"):
        st.session_state.lesson_destination = "Advisor"
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
