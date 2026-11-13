"""Expandable evidence, real-vector inspection, and measured timings."""
import json
import inspect
import numpy as np
import streamlit as st
from .catalog import build_evidence
from .planning import format_duration
from .retrieval import project_embeddings
from .inspection_views import ranking_html


@st.fragment
def render_inspector(result, catalog):
    panel = st.expander("How this plan was made", key="plan_inspector", on_change="rerun")
    if not panel.open:
        return
    records = {r.record_id:r for r in catalog.records}
    sources = {s.source_id:s for s in catalog.sources}
    with panel:
        st.caption("Scores measure relevance, not eligibility or probability. The AI selects statements; the app supplies their wording and citations.")
        st.write(" · ".join(name.replace("_", " ").title()+": "+format_duration(value) for name,value in result.timings.items()))
        st.caption("Index cache: "+result.cache_state+". Total timing excludes browser rendering.")
        phases = result.trace.get("request_phases")
        if phases:
            st.caption("Request stages are timed on the server through result assembly, before provider cleanup and browser rendering.")
            st.dataframe([{"Stage": phase["label"], "Seconds": round(phase["seconds"], 4)}
                          for phase in phases["phases"]], hide_index=True)
        budget = result.trace.get("ai_budget")
        if budget:
            st.caption(f"AI time budget: {budget['limit_seconds']} s · {format_duration(budget['elapsed_seconds'])} used. Source checks are timed separately.")
        checks = result.trace.get("source_refresh", {}).get("checks", [])
        reused = [check for check in checks if check["status"] == "recent_cache"]
        if reused:
            st.caption(f"Reused {len(reused)} recently checked public sources. Their successful check times are unchanged.")
        retried = [check for check in checks if check.get("retry_count", 0)]
        if retried:
            recovered = sum(check["status"] in {"updated", "unchanged", "not_modified"} for check in retried)
            label = "check" if len(retried) == 1 else "checks"
            st.caption(f"Source recovery: {len(retried)} {label} retried · {recovered} recovered. Attempt details are in the request trace.")
        added_terms = result.trace.get("query_interpretation", {}).get("added_terms", [])
        if added_terms:
            st.caption("Search also uses: " + ", ".join(added_terms) + ". These search terms do not change academic requirements.")
        discovery = result.trace.get("source_refresh", {}).get("discovery_selection", {})
        if discovery.get("skipped_completed_codes"):
            st.caption("Discovery slots skip courses recorded as completed: " + ", ".join(discovery["skipped_completed_codes"]) + ".")
        if discovery.get("skipped_enrolled_codes"):
            st.caption("Discovery slots skip courses recorded as currently taking: " + ", ".join(discovery["skipped_enrolled_codes"]) + ".")
        if discovery.get("requested_codes"):
            st.caption("Course discovery prioritizes explicit course mentions and reviewed phrases within the configured source scope and download limit.")
            st.dataframe(discovery["requests"], hide_index=True)
            if discovery.get("truncated"):
                st.caption("Only the first 16 distinct course mentions were considered for discovery priority.")
        hits = [h for h in result.hits if records[h.record_id].kind!="career"][:10]
        if hits:
            def hit_label(hit):
                label = records[hit.record_id].code or records[hit.record_id].title
                return label + (" · prerequisite source" if ":rule:" in hit.chunk_id else "")
            st.html(ranking_html([(hit_label(h), h.score) for h in hits], result.retrieval_mode))
            st.caption("Bars share a zero baseline and are scaled to the largest absolute score. The table keeps the original values.")
            st.dataframe([{"record":h.record_id,"chunk":h.chunk_id,"method":h.method,"score":h.score,
                           "BM25":h.keyword_score,"cosine":h.cosine_score} for h in hits],hide_index=True)
        if result.vectors is not None:
            import plotly.graph_objects as go

            chunks = build_evidence(catalog)
            points, query_point = project_embeddings(result.vectors,result.query_vector)
            labels = [(records[e.record_id].code or records[e.record_id].title)
                      + (" · prerequisite source" if ":rule:" in e.chunk_id else "") for e in chunks]
            chart = go.Figure(go.Scatter(x=points[:,0],y=points[:,1],mode="markers",text=labels,
                marker=dict(size=11,color="#78B8FF"),hovertemplate="%{text}<extra></extra>",name="Records"))
            chart.add_trace(go.Scatter(x=[query_point[0]],y=[query_point[1]],mode="markers",
                marker=dict(size=17,symbol="star",color="#FFD17A"),name="Your query"))
            chart.update_layout(template="plotly_dark",height=320,xaxis_title="PCA 1",yaxis_title="PCA 2")
            st.plotly_chart(chart,width="stretch")
            st.caption("PCA projects real vectors to two dimensions. Ranking uses their full dimensions.")
            index = st.selectbox("Inspect a record vector",range(len(chunks)),format_func=lambda i:labels[i])
            vector, query = result.vectors[index],result.query_vector
            dot = float(np.dot(query,vector))
            qnorm,dnorm = float(np.linalg.norm(query)),float(np.linalg.norm(vector))
            st.latex(r"\operatorname{cosine}(q,d)=\frac{q\cdot d}{\|q\|\|d\|}")
            st.write(f"{len(vector)} dimensions · dot product {dot:.5f} · norms {qnorm:.5f}, {dnorm:.5f}")
            st.json({"query_first_12_dimensions":query[:12].tolist(),"record_first_12_dimensions":vector[:12].tolist(),
                     "cosine_similarity":dot/(qnorm*dnorm)})
        else:
            st.caption("The vector view appears after a successful semantic or hybrid request.")
        code_panel = st.expander("Visualization code", key="plan_visualization_code", on_change="rerun")
        if code_panel.open:
            with code_panel:
                st.caption("The ranking bars and PCA projection use these functions.")
                st.code(inspect.getsource(ranking_html) + "\n\n" + inspect.getsource(project_embeddings),
                        language="python", line_numbers=True)
        for chunk in result.context.evidence:
            st.markdown("**"+chunk.chunk_id+"**")
            st.text(chunk.text)
            for sid in chunk.source_ids:
                st.link_button(sources[sid].title,sources[sid].url,key="trace_"+chunk.chunk_id+"_"+sid)
        if result.context.allowed_statements:
            with st.expander("Available explanation statements"):
                selected = set(result.selected_statement_ids)
                st.dataframe([{"selected": s.statement_id in selected, "statement": s.statement_id,
                    "record": s.record_id, "field": s.field, "kind": s.claim_type,
                    "wording": s.text, "evidence": ", ".join(s.evidence_ids)}
                    for s in result.context.allowed_statements], hide_index=True)
        st.json(result.trace)
        st.download_button("Download request trace",json.dumps(result.trace,indent=2),file_name="request_trace.json",mime="application/json",on_click="ignore")
