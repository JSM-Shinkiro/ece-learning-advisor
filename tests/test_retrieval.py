import numpy as np
import pytest

from src.catalog import build_evidence
from src.models import Completion, StudentProfile
from src.retrieval import Retriever, normalized, project_embeddings
from src.service import recommend


def test_goal_changes_results(catalog):
    ai=recommend(catalog,StudentProfile(career_id="ai_ml",programming_background="experienced"))
    embedded=recommend(catalog,StudentProfile(career_id="embedded",programming_background="experienced"))
    assert ai.context.allowed_record_ids[0]=="uofa:ECE425:2026-2027"
    assert embedded.context.allowed_record_ids[0]=="uofa:ECE372A:2026-2027"


@pytest.mark.parametrize("career,goal",[("ai_ml","ECE425"),("embedded","ECE372A")])
def test_beginner_gets_foundations_before_later_goal(catalog,career,goal):
    result=recommend(catalog,StudentProfile(career_id=career))
    assert result.context.allowed_record_ids[0]=="uofa:ECE101:2026-2027"
    assert result.context.suggested_phases["uofa:ECE101:2026-2027"]=="next"
    assert result.context.suggested_phases[f"uofa:{goal}:2026-2027"]=="later"


def test_completed_foundation_overrides_default_background(catalog):
    profile=StudentProfile(career_id="ai_ml",completed=[Completion(course_code="ECE101")])
    result=recommend(catalog,profile)
    assert result.context.allowed_record_ids[0]=="uofa:ECE425:2026-2027"
    assert "uofa:ECE101:2026-2027" not in result.context.allowed_record_ids


def test_standing_alone_does_not_imply_programming_experience(catalog):
    result=recommend(catalog,StudentProfile(standing="Senior",career_id="ai_ml"))
    assert result.context.allowed_record_ids[0]=="uofa:ECE101:2026-2027"


def test_completed_courses_leave_next_steps(catalog):
    result=recommend(catalog,StudentProfile(career_id="embedded",completed=[Completion(course_code="ECE372A")]))
    assert "uofa:ECE372A:2026-2027" not in result.context.allowed_record_ids


def test_exact_spaced_code(catalog):
    hits=Retriever(build_evidence(catalog)).keyword("ECE 425")
    assert hits[0].record_id=="uofa:ECE425:2026-2027"


def test_no_match_is_not_a_forced_recommendation(catalog):
    assert Retriever(build_evidence(catalog)).keyword("zzzznotaword")==[]


@pytest.mark.parametrize("vectors",[[[0,0]],[[float("nan"),1]],[[float("inf"),1]]])
def test_invalid_vectors(vectors):
    with pytest.raises(ValueError):
        normalized(vectors)


def test_dimension_mismatch(catalog):
    chunks=build_evidence(catalog)
    retriever=Retriever(chunks,np.ones((len(chunks),3)))
    with pytest.raises(ValueError):
        retriever.semantic([1,2])


def test_pca_record_positions_stay_fixed():
    values=[[1,0,1],[0,1,1],[1,1,0]]
    first,_=project_embeddings(values,[1,0,1])
    second,_=project_embeddings(values,[0,1,1])
    np.testing.assert_allclose(first,second)


def test_vector_row_count_mismatch(catalog):
    with pytest.raises(ValueError):
        Retriever(build_evidence(catalog),[[1,0]])
