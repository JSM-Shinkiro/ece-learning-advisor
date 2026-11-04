"""Expandable evidence, real-vector inspection, and measured timings."""
import json
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from .catalog import build_evidence
from .planning import format_duration
from .retrieval import project_embeddings


def render_inspector(result, catalog):
    records = {r.record_id:r for r in catalog.records}
    sources = {s.source_id:s for s in catalog.sources}
    with st.expander("How this plan was made"):
        st.caption("Scores measure relevance, not eligibility or probability. Source-link checks do not prove every generated claim.")
        st.write(" · ".join(name.replace("_", " ").title()+": "+format_duration(value) for name,value in result.timings.items()))
        st.caption("Index cache: "+result.cache_state+". Total timing excludes browser rendering.")
        hits = [h for h in result.hits if records[h.record_id].kind!="career"][:10]
        if hits:
            chart = go.Figure(go.Bar(x=[h.score for h in hits],
                y=[records[h.record_id].code or records[h.record_id].title for h in hits],
                orientation="h", marker_color="#78B8FF"))
            chart.update_layout(template="plotly_dark", height=300, margin=dict(l=5,r=10,t=10,b=10),
                xaxis_title=result.retrieval_mode+" ranking score", yaxis=dict(autorange="reversed"))
            st.plotly_chart(chart, width="stretch")
            st.dataframe([{"record":h.record_id,"method":h.method,"score":h.score,
                           "BM25":h.keyword_score,"cosine":h.cosine_score} for h in hits],hide_index=True)
        if result.vectors is not None:
            chunks = build_evidence(catalog)
            points, query_point = project_embeddings(result.vectors,result.query_vector)
            labels = [records[e.record_id].code or records[e.record_id].title for e in chunks]
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
        for chunk in result.context.evidence:
            st.markdown("**"+chunk.chunk_id+"**")
            st.text(chunk.text)
            for sid in chunk.source_ids:
                st.link_button(sources[sid].title,sources[sid].url,key="trace_"+chunk.chunk_id+"_"+sid)
        st.json(result.trace)
        st.download_button("Download request trace",json.dumps(result.trace,indent=2),file_name="request_trace.json",mime="application/json")
