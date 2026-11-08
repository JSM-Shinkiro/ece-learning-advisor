import pytest
import time
from pathlib import Path
from streamlit.testing.v1 import AppTest


@pytest.fixture
def app(monkeypatch):
    # Preserve the historical five-course interaction scenarios. Expanded app
    # defaults have their own integration cases in test_runtime_catalog.py.
    from src.catalog import load_catalog
    monkeypatch.setattr("src.catalog.load_runtime_catalog", load_catalog)
    monkeypatch.setattr("src.course_directory.load_course_directory", lambda:None)
    monkeypatch.setattr("dotenv.load_dotenv",lambda *a,**k:False)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "false")
    for name in ["GEMINI_API_KEY","GOOGLE_API_KEY","ADZUNA_APP_ID","ADZUNA_APP_KEY","ECE_DEVELOPMENT_MODE"]:
        monkeypatch.delenv(name,raising=False)
    return AppTest.from_file(Path(__file__).resolve().parents[1]/"app.py",default_timeout=20).run()


def submit(app):
    next(b for b in app.button if b.label=="Update my roadmap").click()
    app.run()
    return settle_advisor(app)


def settle_advisor(app, timeout=10):
    deadline = time.monotonic() + timeout
    while "advisor_job" in app.session_state:
        assert time.monotonic() < deadline, "The controlled advisor request did not finish"
        app.session_state["advisor_job"].wait(0.05)
        app.run()
    return app


def open_inspector(app):
    app.session_state["plan_inspector"] = True
    app.run()
    assert not app.exception


def test_profile_to_roadmap_and_goal_change(app):
    assert not app.exception
    submit(app)
    assert not app.exception
    assert any("ECE425" in h.value for h in app.markdown)
    assert any(h.value=="Later goals" for h in app.subheader)
    assert app.session_state["result"].context.allowed_record_ids[0]=="uofa:ECE101:2026-2027"
    app.selectbox(key="career_id").set_value("embedded")
    app.selectbox(key="programming_background").set_value("experienced")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.session_state["profile"].programming_background=="experienced"
    assert app.session_state["result"].context.allowed_record_ids[0]=="uofa:ECE372A:2026-2027"
    assert not app.session_state["result"].generation_complete


def test_completed_course_updates_ui(app):
    app.selectbox(key="career_id").set_value("embedded")
    app.text_area(key="course_text").set_value("ECE372A:B")
    submit(app)
    assert not app.exception
    assert "uofa:ECE372A:2026-2027" not in app.session_state["result"].context.allowed_record_ids


def test_invalid_profile_is_visible_error(app):
    app.text_area(key="course_text").set_value("ECE101, ECE 101")
    submit(app)
    assert not app.exception
    assert app.error


@pytest.mark.parametrize("variable,value", [("EMBEDDING_DIMENSION", "private-invalid-dimension"),
    ("ECE_REFRESH_SOURCES", "private-invalid-flag"), ("GENERATION_MODEL", "private-invalid-model")])
def test_invalid_server_configuration_is_a_sanitized_startup_error(app, monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    app.run()
    assert not app.exception
    assert any(variable in item.value for item in app.error)
    assert not any(value in item.value for item in app.error)
    monkeypatch.delenv(variable)
    app.run()
    assert not app.exception and not app.error


def test_configured_cache_root_reaches_the_submitted_backend(app, monkeypatch, tmp_path):
    import src.controller
    original = src.controller.run_advisor
    called = []
    def run(*args, **kwargs):
        called.append(kwargs)
        return original(*args, **kwargs)
    monkeypatch.setattr("src.controller.run_advisor", run)
    monkeypatch.setenv("ECE_CACHE_DIR", str(tmp_path))
    submit(app)
    assert not app.exception
    assert called[0]["cache_dir"] == tmp_path / "embeddings"
    assert called[0]["source_cache_dir"] == tmp_path / "sources"


def test_public_opportunities_are_available_without_adzuna_credentials(app):
    assert not next(b for b in app.button if b.label=="Available Opportunities").disabled
    assert not app.exception
    assert app.selectbox(key="opportunity_provider").value == "greenhouse"
    assert any("Samsara, Nuro" in x.value for x in app.caption)


def opportunity_fixture(*, empty=False, provider="greenhouse", issues=None, role_filter="all"):
    from src.jobs import JobSearchResult
    listings = [] if empty else [{"id": "greenhouse:samsara:12", "title": "Fixture Machine Learning Engineer",
        "employer": "Samsara", "location": "Remote - US", "url": "https://www.samsara.com/company/careers/roles/12?gh_jid=12",
        "posted_at": "2026-09-01T00:00:00+00:00", "updated_at": "2026-11-03T00:00:00+00:00",
        "description_snippet": "", "matched_terms": ["machine learning"]}]
    return JobSearchResult(listings, "2026-11-04T22:00:00+00:00", "machine learning", "Remote - US",
        provider=provider, total_matches=len(listings), issues=issues or [], role_filter=role_filter,
        checks=[{"board": "samsara", "status": "verified"}])


def submit_opportunities(app):
    next(b for b in app.button if b.label == "Available Opportunities").click()
    return app.run()


def test_opportunity_fetch_is_explicit_fresh_by_default_and_cache_reuse_is_visible(app, monkeypatch):
    calls = []
    def search(*args, **kwargs):
        calls.append((args, kwargs))
        return opportunity_fixture()
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    app.run()
    assert calls == []
    submit_opportunities(app)
    assert not app.exception and len(calls) == 1
    assert any(item.value == "Fixture Machine Learning Engineer" for item in app.text)
    assert any("Provider last update:" in item.value for item in app.caption)
    assert any("Opportunity source checks" == item.label for item in app.expander)
    app.run()
    assert len(calls) == 1
    submit_opportunities(app)
    assert len(calls) == 2  # No implicit twenty-minute cache reuse.
    app.checkbox(key="reuse_opportunities").set_value(True)
    submit_opportunities(app)
    assert len(calls) == 2
    assert any("Reused recent results" in item.value for item in app.caption)


def test_public_opportunity_filters_reach_backend_on_submission(app, monkeypatch):
    calls = []
    def search(*args, **kwargs):
        calls.append((args, kwargs)); return opportunity_fixture(empty=True)
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    app.text_input(key="opportunity_location_greenhouse").set_value("Tucson")
    app.selectbox(key="opportunity_role_titles").set_value("internship")
    app.selectbox(key="opportunity_age").set_value(7)
    submit_opportunities(app)
    assert not app.exception
    assert len(calls) == 1 and calls[0][0] == ("ai_ml", "Tucson", True)
    assert calls[0][1]["updated_within"] == 7 and calls[0][1]["early_career"] is False
    assert [b.token for b in calls[0][1]["boards"]] == ["samsara", "nuro", "andurilindustries"]
    assert any("No listings were returned" in item.value for item in app.info)


def test_recovered_employer_requests_show_attempt_history_without_retrying_on_rerenders(app, monkeypatch):
    import httpx
    from collections import Counter
    from src.opportunities import load_employer_boards, search_employer_jobs
    from test_opportunities import NOW, post
    calls = Counter()
    boards = {b.token: b for b in load_employer_boards()}
    def search(*args, **kwargs):
        def respond(request):
            token = request.url.path.split("/")[3]
            calls[token] += 1
            if calls[token] == 1: return httpx.Response(503)
            return httpx.Response(200, json={"jobs": [post(boards[token])]})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return search_employer_jobs(*args, **kwargs, client=client, now=NOW)
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    submit_opportunities(app)
    assert not app.exception and set(calls.values()) == {2}
    result = app.session_state["job_result"]
    assert all(c["retry_count"] == 1 and len(c["attempts"]) == 2 for c in result.checks)
    table = next(item.value for item in app.dataframe if "retry_count" in item.value.columns)
    assert table["retry_count"].tolist() == [1, 1, 1]
    assert sum("HTTP attempts" in c.value for c in app.caption) == 3
    app.run()
    assert not app.exception and set(calls.values()) == {2}


def test_recovered_posting_details_show_safe_attempts_and_do_not_recheck_on_rerender(app, monkeypatch):
    import httpx
    from src.opportunity_details import fetch_posting_detail
    from test_opportunities import NOW, post
    calls = []
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: opportunity_fixture())
    def fetch(job, **kwargs):
        def respond(request):
            calls.append(1)
            if len(calls) == 1: raise httpx.ReadTimeout("private-detail-diagnostic")
            return httpx.Response(200, json={**post(), "content": "Checked recovered description"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return fetch_posting_detail(job, **{**kwargs, "now": NOW}, client=client)
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", fetch)
    submit_opportunities(app)
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    assert not app.exception and len(calls) == 2
    assert any("2 HTTP attempt(s) · 1 retry" in c.value for c in app.caption)
    assert any(e.label == "Posting request attempts" for e in app.expander)
    assert any(t.value == "Checked recovered description" for t in app.text)
    assert "private-detail-diagnostic" not in app.session_state["job_detail"].model_dump_json()
    app.run()
    assert not app.exception and len(calls) == 2


def test_opportunity_page_controls_browse_the_same_snapshot_without_network_or_unsubmitted_filters(app, monkeypatch):
    import httpx
    from test_opportunity_pages import paged_result
    result, calls = paged_result(), []
    def search(*a, **k): calls.append(1); return result
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    submit_opportunities(app)
    assert not app.exception and app.button(key="opportunity_previous").disabled
    assert any("Showing 1–10 of 23" in item.value for item in app.caption)
    monkeypatch.setattr(httpx.Client, "send", lambda *a, **k: pytest.fail("Navigation must not fetch"))
    app.selectbox(key="opportunity_role_titles").set_value("early_career")
    app.button(key="opportunity_next").click().run()
    assert not app.exception and app.session_state["job_result"].page == 1
    assert any("Showing 11–20 of 23" in item.value for item in app.caption)
    assert any("Results title filter: All levels" in item.value for item in app.caption)
    assert not any("Results title filter: New grad" in item.value for item in app.caption)
    assert app.session_state["job_result"].retrieved_at == result.retrieved_at
    assert not any(item.value == result.listings[0]["title"] for item in app.text)
    app.button(key="opportunity_next").click().run()
    assert not app.exception and app.button(key="opportunity_next").disabled
    assert any("Showing 21–23 of 23" in item.value for item in app.caption)
    assert len(app.session_state["job_result"].listings) == 3
    app.button(key="opportunity_previous").click().run()
    app.run()
    assert not app.exception and calls == [1] and app.session_state["job_result"].page == 1


def test_page_changes_clear_checked_descriptions_and_later_page_detail_actions_still_work(app, monkeypatch):
    from test_opportunity_pages import paged_result
    from test_opportunity_details import checked
    from test_opportunities import post
    result, calls = paged_result(), []
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: result)
    def fetch(job, **kwargs):
        calls.append(job["id"])
        return checked({**post(identity=int(job["id"].split(":")[-1])), "content": "Checked description " + job["id"]}, job=job)
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", fetch)
    submit_opportunities(app)
    first_id = result.listings[0]["id"]
    app.button(key="job_detail_" + first_id).click().run()
    app.button(key="opportunity_next").click().run()
    assert not app.exception and "job_detail" not in app.session_state
    assert not any("Checked description" in item.value for item in app.text)
    selected_id = app.session_state["job_result"].listings[0]["id"]
    app.button(key="job_detail_" + selected_id).click().run()
    assert not app.exception and calls == [first_id, selected_id]
    assert any(item.value == "Checked description " + selected_id for item in app.text)


def test_fresh_search_and_explicit_result_reuse_both_restart_at_page_one(app, monkeypatch):
    from test_opportunity_pages import paged_result
    calls = []
    def search(*a, **k): calls.append(1); return paged_result()
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    submit_opportunities(app)
    app.button(key="opportunity_next").click().run()
    app.checkbox(key="reuse_opportunities").set_value(True)
    submit_opportunities(app)
    assert not app.exception and calls == [1] and app.session_state["job_result"].page == 0
    assert any("Reused recent results" in item.value for item in app.caption)
    app.button(key="opportunity_next").click().run()
    app.checkbox(key="reuse_opportunities").set_value(False)
    submit_opportunities(app)
    assert not app.exception and calls == [1, 1] and app.session_state["job_result"].page == 0


@pytest.mark.parametrize("count", [0, 1, 10])
def test_one_page_or_empty_opportunity_results_do_not_offer_navigation(app, monkeypatch, count):
    from test_opportunity_pages import paged_result
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: paged_result(count))
    submit_opportunities(app)
    assert not app.exception
    assert not any(b.key in {"opportunity_previous", "opportunity_next"} for b in app.button)


def test_capped_snapshot_explains_that_additional_matches_need_narrower_filters(app, monkeypatch):
    from test_opportunity_pages import paged_result
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: paged_result(201))
    submit_opportunities(app)
    assert not app.exception and any("retains the first 200 matches" in item.value for item in app.info)
    assert any("Page 1 of 20" in item.value for item in app.caption)


def test_rejected_navigation_is_visible_and_a_new_search_clears_the_page_error(app, monkeypatch):
    from test_opportunity_pages import paged_result
    from src.opportunities import load_employer_boards
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: paged_result())
    submit_opportunities(app)
    boards = load_employer_boards()
    boards[0].employer = "Changed configuration"
    monkeypatch.setattr("src.opportunity_pages.load_employer_boards", lambda: boards)
    app.button(key="opportunity_next").click().run()
    assert not app.exception and app.session_state["job_result"].page == 0
    assert any("saved search page could not be opened" in item.value for item in app.warning)
    submit_opportunities(app)
    assert not app.exception and "job_page_error" not in app.session_state


def test_failed_opportunity_search_removes_previous_results(app, monkeypatch):
    failing = False
    def search(*args, **kwargs):
        if failing:
            raise RuntimeError("private provider diagnostic")
        return opportunity_fixture()
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    submit_opportunities(app)
    failing = True
    submit_opportunities(app)
    assert not app.exception
    assert any("could not complete this search" in item.value for item in app.warning)
    assert not any(item.value == "Fixture Machine Learning Engineer" for item in app.text)
    assert "job_result" not in app.session_state
    assert not any("private provider diagnostic" in item.value for item in app.warning)


@pytest.mark.parametrize("role,internship,early,label", [("early_career", False, True, "New grad / entry-level"),
    ("internship", True, False, "Internship / co-op")])
def test_student_role_choices_reach_the_backend_and_reuse_only_matching_results(app, monkeypatch, role, internship, early, label):
    calls = []
    def search(*a, **k):
        calls.append((a, k))
        return opportunity_fixture(role_filter="internship" if a[2] else "early_career" if k["early_career"] else "all")
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    assert any("Anduril Industries" in c.value for c in app.caption)
    app.selectbox(key="opportunity_role_titles").set_value(role)
    submit_opportunities(app)
    assert not app.exception and len(calls) == 1
    assert calls[0][0][2] is internship and calls[0][1]["early_career"] is early
    assert any("Results title filter: " + label in c.value for c in app.caption)
    app.run()
    assert len(calls) == 1
    app.checkbox(key="reuse_opportunities").set_value(True)
    submit_opportunities(app)
    assert len(calls) == 1
    app.selectbox(key="opportunity_role_titles").set_value("all")
    submit_opportunities(app)
    assert len(calls) == 2 and any("Results title filter: All levels" in c.value for c in app.caption)


def test_unsubmitted_role_change_keeps_the_displayed_result_filter_label(app, monkeypatch):
    calls = []
    def search(*a, **k): calls.append(1); return opportunity_fixture(role_filter="all")
    monkeypatch.setattr("src.opportunities.search_employer_jobs", search)
    submit_opportunities(app)
    app.selectbox(key="opportunity_role_titles").set_value("early_career").run()
    assert not app.exception and calls == [1]
    assert any("Results title filter: All levels" in c.value for c in app.caption)
    assert not any("Results title filter: New grad / entry-level" in c.value for c in app.caption)


def test_posting_details_require_an_explicit_action_and_rerenders_keep_the_original_check_time(app, monkeypatch):
    from test_opportunity_details import checked
    calls = []
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: opportunity_fixture())
    def fetch(job, **kwargs): calls.append(job["id"]); return checked()
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", fetch)
    submit_opportunities(app)
    assert calls == []
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    assert not app.exception and calls == ["greenhouse:samsara:12"]
    assert any("Review degree requirements" in item.value for item in app.text)
    assert any("Checked posting's publication date:" in item.value for item in app.caption)
    first = app.session_state["job_detail"].checked_at
    app.run()
    assert calls == ["greenhouse:samsara:12"] and app.session_state["job_detail"].checked_at == first
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    assert len(calls) == 2 and not app.exception
    app.checkbox(key="reuse_opportunities").set_value(True)
    submit_opportunities(app)
    assert "job_detail" not in app.session_state
    assert not any("Review degree requirements" in item.value for item in app.text)


@pytest.mark.parametrize("status,phrase", [(404, "not found at the source"), (429, "could not be reached")])
def test_failed_posting_recheck_removes_old_description_and_shows_a_dated_failure(app, monkeypatch, status, phrase):
    import httpx
    from test_opportunity_details import checked
    outcomes = iter([checked(), checked(httpx.Response(status))])
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: opportunity_fixture())
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", lambda *a, **k: next(outcomes))
    submit_opportunities(app)
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    assert not app.exception and any(phrase in item.value for item in app.warning)
    assert any("Posting check attempted:" in item.value for item in app.caption)
    assert not any("Review degree requirements" in item.value for item in app.text)


def test_changed_posting_title_is_displayed_with_a_search_snapshot_warning(app, monkeypatch):
    from test_opportunity_details import checked
    from test_opportunities import post
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: opportunity_fixture())
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", lambda *a, **k:
        checked({**post(), "title": "Senior Firmware Engineer", "content": "Updated requirements"}))
    submit_opportunities(app)
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    assert not app.exception and any("Senior Firmware Engineer" == item.value for item in app.text)
    assert any("Search filters have not been rerun" in item.value for item in app.info)
    submit(app)
    assert "job_detail" not in app.session_state


def test_selecting_a_second_posting_shows_only_its_checked_description(app, monkeypatch):
    from test_opportunity_details import checked, selected
    from test_opportunities import post
    jobs = opportunity_fixture()
    jobs.listings.append(selected(identity=13))
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: jobs)
    def fetch(job, **kwargs):
        identity = int(job["id"].split(":")[-1])
        return checked({**post(identity=identity), "content": "Description " + str(identity)}, job=job)
    monkeypatch.setattr("src.opportunity_details.fetch_posting_detail", fetch)
    submit_opportunities(app)
    app.button(key="job_detail_greenhouse:samsara:12").click().run()
    app.button(key="job_detail_greenhouse:samsara:13").click().run()
    assert not app.exception and any(item.value == "Description 13" for item in app.text)
    assert not any(item.value == "Description 12" for item in app.text)


def test_partial_opportunity_source_issue_is_shown_with_usable_listings(app, monkeypatch):
    monkeypatch.setattr("src.opportunities.search_employer_jobs", lambda *a, **k: opportunity_fixture(issues=["Nuro: this board could not be checked; its listings are omitted."]))
    submit_opportunities(app)
    assert not app.exception
    assert any("Nuro: this board could not be checked" in item.value for item in app.warning)
    assert any(item.value == "Fixture Machine Learning Engineer" for item in app.text)


def test_complete_provider_failure_exposes_source_checks_without_fake_empty_results(app, monkeypatch):
    from src.opportunities import OpportunitySearchError
    def fail(*args, **kwargs):
        raise OpportunitySearchError([{"board": "samsara", "status": "unavailable", "http_status": 429}])
    monkeypatch.setattr("src.opportunities.search_employer_jobs", fail)
    submit_opportunities(app)
    assert not app.exception
    assert any(item.label == "Last search source checks" for item in app.expander)
    assert not any("No listings were returned" in item.value for item in app.info)


def test_opportunity_search_waits_for_a_career_direction(app, monkeypatch):
    def forbidden(*args, **kwargs): pytest.fail("Exploring profile must not fetch jobs")
    monkeypatch.setattr("src.opportunities.search_employer_jobs", forbidden)
    app.selectbox(key="career_id").set_value("exploring")
    submit(app)
    assert not app.exception
    assert next(b for b in app.button if b.label == "Available Opportunities").disabled


def test_adzuna_is_an_explicit_separate_source_when_configured(app, monkeypatch):
    calls = []
    def adzuna(*args): calls.append(args); return opportunity_fixture(empty=True, provider="adzuna")
    def forbidden(*args, **kwargs): pytest.fail("Do not silently switch to employer boards")
    monkeypatch.setenv("ADZUNA_APP_ID", "fixture-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "fixture-key")
    monkeypatch.setattr("src.jobs.search_jobs", adzuna)
    monkeypatch.setattr("src.opportunities.search_employer_jobs", forbidden)
    app.run()
    app.selectbox(key="opportunity_provider").set_value("adzuna").run()
    submit_opportunities(app)
    assert not app.exception
    assert calls == [("fixture-id", "fixture-key", "ai_ml", "Tucson, AZ", False)]
    assert app.session_state["job_result"].provider == "adzuna"


def test_invalid_employer_configuration_keeps_the_rest_of_the_app_usable(app, monkeypatch):
    def fail(*a, **k): raise ValueError("configuration detail")
    monkeypatch.setattr("src.opportunities.load_employer_boards", fail)
    app.run()
    assert not app.exception
    assert any("employer-board connection is unavailable" in item.value for item in app.warning)
    assert next(b for b in app.button if b.label == "Available Opportunities").disabled


def test_live_ui_with_controlled_provider(app,monkeypatch,fake_provider):
    import src.controller
    original=fake_provider.generate
    def with_multiple_reasons(context):
        answer=original(context)
        item = answer.recommendations[0]
        extra = next(s for s in context.allowed_statements if s.record_id == item.record_id and s.statement_id not in item.statement_ids)
        item.statement_ids.append(extra.statement_id)
        return answer
    fake_provider.generate=with_multiple_reasons
    fake_provider.close=lambda:None
    monkeypatch.setattr(src.controller,"GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","fixture-key")
    app.run()
    app.checkbox(key="use_ai").set_value(True)
    app.run()
    submit(app)
    open_inspector(app)
    assert not app.exception
    assert app.session_state["result"].generation_complete
    assert fake_provider.context is app.session_state["result"].context
    assert app.session_state["result"].statement_validation_passed
    assert any(expander.label == "Available explanation statements" for expander in app.expander)
    table = next(item.value for item in app.dataframe if "statement" in item.value.columns)
    assert table["selected"].sum() == 2
    assert set(table[table["selected"]]["statement"]) == set(app.session_state["result"].selected_statement_ids)


def test_rejected_explanation_keeps_sources_and_never_displays_its_prose(app, monkeypatch, fake_provider):
    from src.models import GeneratedAnswer, Reason, Recommendation
    def legacy(context):
        rid = context.allowed_record_ids[0]
        return GeneratedAnswer(status="answered", recommendations=[Recommendation(record_id=rid,
            reasons=[Reason(text="Guaranteed internship from this course.", claim_type="recommendation",
                evidence_ids=[rid + ":overview"])])])
    fake_provider.generate = legacy
    fake_provider.close = lambda: None
    monkeypatch.setattr("src.controller.GeminiProvider", lambda *a, **k: fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY", "fixture-key")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception and app.warning
    result = app.session_state["result"]
    assert result.answer is None and result.trace["validation_error"] == "unsupported_output"
    assert any(button.key == "complete_ECE101" for button in app.button)
    assert not any("Guaranteed internship" in item.value for item in app.markdown)
    assert not any("AI explanation available" in item.value for item in app.caption)


def test_server_key_never_populates_widget(app,monkeypatch):
    secret="dummy-server-secret"
    monkeypatch.setenv("GEMINI_API_KEY",secret)
    monkeypatch.setenv("ECE_DEVELOPMENT_MODE","true")
    app.run()
    assert not app.exception
    assert all(w.value!=secret for w in app.text_input)
    assert not any(w.key=="gemini_key" for w in app.text_input)


def test_initialization_failure_updates_profile_and_roadmap_together(app,monkeypatch):
    from src.providers import ProviderError
    submit(app)
    assert app.session_state["result"].context.profile.career_id=="ai_ml"
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    def fail(*args,**kwargs):
        raise ProviderError("Test failure")
    monkeypatch.setattr("src.controller.GeminiProvider",fail)
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.session_state["result"].context.profile.career_id=="embedded"
    assert app.warning


def test_imported_fields_survive_form_edit(app):
    from src.models import StudentProfile
    app.session_state["profile"]=StudentProfile(current_enrollment=["MATH129"],consents=["permission"])
    app.session_state["reset_profile_widgets"]=True
    app.run()
    app.text_area(key="interests").set_value("robotics")
    submit(app)
    assert not app.exception
    assert app.session_state["profile"].current_enrollment==["MATH129"]
    assert app.session_state["profile"].consents==["permission"]


def test_mark_completed_refreshes_plan_and_visible_picker(app):
    submit(app)
    app.button(key="complete_ECE101").click().run()
    assert not app.exception
    assert "ECE101" in app.multiselect(key="completed_courses").value
    assert "uofa:ECE101:2026-2027" not in app.session_state["result"].context.allowed_record_ids
    assert any("Added to completed" in caption.value for caption in app.caption)


def test_exploring_offers_both_goals_and_selectable_direction(app):
    app.selectbox(key="career_id").set_value("exploring")
    app.text_area(key="interests").set_value("AI and Hardware Integration")
    submit(app)
    assert not app.exception
    allowed=app.session_state["result"].context.allowed_record_ids
    assert {"uofa:ECE425:2026-2027","uofa:ECE372A:2026-2027"} <= set(allowed)
    app.button(key="choose_embedded").click().run()
    assert not app.exception
    assert app.session_state["profile"].career_id=="embedded"
    assert app.selectbox(key="career_id").value=="embedded"


def test_unsupported_question_shows_clarification_instead_of_courses(app):
    app.text_input(key="question").set_value("I want a marine biology degree and ocean fieldwork")
    submit(app)
    assert not app.exception
    assert app.session_state["result"].coverage_notice
    assert not any(button.key and button.key.startswith("complete_") for button in app.button)


@pytest.mark.parametrize("career,question,code", [("ai_ml", "train computers to pick out patterns from pictures", "ECE425"),
    ("embedded", "make a little board react when a button is pressed without polling", "ECE372A")])
def test_paraphrased_interest_reaches_roadmap_and_visible_search_terms(app, career, question, code):
    app.selectbox(key="career_id").set_value(career)
    app.text_input(key="question").set_value(question)
    submit(app)
    open_inspector(app)
    assert not app.exception
    result = app.session_state["result"]
    assert not result.coverage_notice and f"uofa:{code}:2026-2027" in result.context.allowed_record_ids
    assert any("Search also uses:" in item.value for item in app.caption)
    assert result.context.rule_results[f"uofa:{code}:2026-2027"].status == "unknown"


def test_discovered_reviewed_condition_reaches_picker_card_and_inspector(app, monkeypatch, tmp_path):
    from test_discovered_rules import rule_client, refresh
    calls = []
    def refresher(catalog, profile, **kwargs):
        calls.append(profile.question)
        with rule_client(catalog) as client:
            return refresh(catalog, client, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresher)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_area(key="course_text").set_value("MATH112:B")
    app.text_input(key="question").set_value("CSC110")
    submit(app)
    open_inspector(app)
    assert not app.exception
    result = app.session_state["result"]
    assert result.context.rule_results["uofa:CSC110:2026-2027"].status == "satisfied"
    assert any("Recorded prerequisites satisfied" in item.value for item in app.caption)
    assert any("uofa:CSC110:2026-2027:rule:R1299-L30" in item.value for item in app.markdown)
    app.run()
    assert any(option.startswith("CSC110 · ") for option in app.multiselect(key="completed_courses").options)
    assert calls == ["CSC110"]


@pytest.mark.parametrize("code,section", [("CSC144", "R1299-L50"), ("CSC210", "R1299-L70")])
def test_expanded_cs_conditions_reach_the_roadmap_picker_and_sources(app, monkeypatch, tmp_path, code, section):
    from test_cs_foundations import expanded_refresh
    calls = []
    def refresher(catalog, profile, **kwargs):
        calls.append(profile.question)
        return expanded_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresher)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_area(key="course_text").set_value("ECE101:B, MATH112:B, CSC120:B")
    app.selectbox(key="programming_background").set_value("experienced")
    app.text_input(key="question").set_value(code)
    submit(app)
    open_inspector(app)
    assert not app.exception
    result = app.session_state["result"]
    rid = "uofa:" + code + ":2026-2027"
    assert rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status == "satisfied"
    assert result.context.rule_results[rid].verification_status == "verified"
    assert any(rid + ":rule:" + section in item.value for item in app.markdown)
    app.run()
    assert any(option.startswith(code + " · ") for option in app.multiselect(key="completed_courses").options)
    assert calls == [code]


@pytest.mark.parametrize("code", ["ECE201", "ECE274A"])
def test_requested_ece_course_gets_a_discovery_slot_and_visible_selection_status(app, monkeypatch, tmp_path, code):
    from test_discovery_priority import priority_refresh
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.question)
        return priority_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_input(key="question").set_value("How should I prepare for " + code + "?")
    submit(app)
    open_inspector(app)
    assert not app.exception
    result = app.session_state["result"]
    rid = "uofa:" + code + ":2026-2027"
    assert rid in result.context.allowed_record_ids
    assert result.context.rule_results[rid].status == "unknown"
    table = next(item.value for item in app.dataframe if {"code", "status"} <= set(item.value.columns))
    assert table[table["code"] == code]["status"].tolist() == ["added"]
    assert any("prioritizes explicit course mentions" in item.value for item in app.caption)
    app.run()
    assert any(option.startswith(code + " · ") for option in app.multiselect(key="completed_courses").options)
    assert calls == ["How should I prepare for " + code + "?"]


def test_unavailable_course_displays_selection_limit_without_a_fabricated_card(app, monkeypatch, tmp_path):
    from test_discovery_priority import priority_refresh
    monkeypatch.setattr("src.controller.refresh_catalog", lambda catalog, profile, **kwargs: priority_refresh(catalog, tmp_path, profile))
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_input(key="question").set_value("ECE499")
    submit(app)
    open_inspector(app)
    assert not app.exception
    assert app.session_state["result"].coverage_notice
    table = next(item.value for item in app.dataframe if {"code", "status"} <= set(item.value.columns))
    assert table[table["code"] == "ECE499"]["status"].tolist() == ["not_available"]
    assert not any(option.startswith("ECE499 · ") for option in app.multiselect(key="completed_courses").options)


@pytest.mark.parametrize("phrase,code", [("phasors", "ECE220"), ("unit testing", "CSC210")])
def test_reviewed_phrase_can_populate_the_roadmap_without_a_course_code(app, monkeypatch, tmp_path, phrase, code):
    from test_discovery_priority import priority_refresh
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.question)
        return priority_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_input(key="question").set_value(phrase)
    submit(app)
    open_inspector(app)
    assert not app.exception
    result = app.session_state["result"]
    assert "uofa:" + code + ":2026-2027" in result.context.allowed_record_ids
    table = next(item.value for item in app.dataframe if {"code", "matched_phrases"} <= set(item.value.columns))
    assert table[table["code"] == code]["status"].tolist() == ["added"]
    assert any("reviewed phrases" in item.value for item in app.caption)
    app.run()
    assert calls == [phrase]


@pytest.mark.parametrize("phrase,code", [("eigenvalues", "ECE310"), ("class hierarchies", "ECE373")])
def test_ece_core_appears_as_preparation_with_unverified_enrollment(app, monkeypatch, tmp_path, phrase, code):
    from test_ece_core import core_refresh
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.question)
        return core_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_input(key="question").set_value(phrase)
    submit(app)
    assert not app.exception
    result = app.session_state["result"]
    rid = "uofa:" + code + ":2026-2027"
    assert rid in result.context.allowed_record_ids and result.context.suggested_phases[rid] == "build"
    assert result.context.rule_results[rid].status == "unknown"
    assert any("Enrollment requirements unverified" in caption.value for caption in app.caption)
    app.run()
    assert any(option.startswith(code + " · ") for option in app.multiselect(key="completed_courses").options)
    assert calls == [phrase]


def test_completed_foundations_skip_download_slots_and_are_visible_in_inspector(app, monkeypatch, tmp_path):
    from test_ece_core import core_refresh
    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.career_id)
        return core_refresh(catalog, tmp_path, profile)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.selectbox(key="career_id").set_value("embedded")
    app.text_area(key="course_text").set_value("ECE201:B, ECE220:B, ECE274A:B")
    submit(app)
    open_inspector(app)
    assert not app.exception
    selection = app.session_state["result"].trace["source_refresh"]["discovery_selection"]
    assert selection["skipped_completed_codes"] == ["ECE201", "ECE220", "ECE274A"]
    assert any("Discovery slots skip courses recorded as completed" in caption.value for caption in app.caption)
    app.run()
    assert calls == ["embedded"]


def test_recovered_source_attempts_are_visible_and_rerenders_do_not_retry(app, monkeypatch, tmp_path):
    import httpx
    from collections import Counter
    from src.sources import refresh_catalog
    from test_sources import course_page
    calls, submitted = Counter(), []
    def refresh(catalog, profile, **kwargs):
        submitted.append(profile.question)
        active = catalog.model_copy(deep=True)
        record = next(r for r in active.records if r.code == "ECE101")
        active.records = [record]
        active.sources = [s for s in active.sources if s.source_id in record.source_ids]
        def respond(request):
            calls[str(request.url)] += 1
            if calls[str(request.url)] == 1: raise httpx.ConnectTimeout("private-retry-detail")
            return httpx.Response(200, text=course_page(record), headers={"Content-Type": "text/html"})
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return refresh_catalog(active, profile, client=client, cache_dir=tmp_path)
    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    submit(app)
    open_inspector(app)
    assert not app.exception
    assert any("1 check retried · 1 recovered" in caption.value for caption in app.caption)
    check = app.session_state["result"].trace["source_refresh"]["checks"][0]
    assert check["retry_count"] == 1 and [a["outcome"] for a in check["attempts"]] == ["timeout", "success"]
    assert "private-retry-detail" not in str(check)
    app.run()
    assert submitted == [""] and sum(calls.values()) == 2


def test_ai_abstention_does_not_show_success_or_recommendations(app,monkeypatch,fake_provider):
    from src.models import ExplanationSelection
    fake_provider.generate=lambda _:ExplanationSelection(status="insufficient_evidence",clarification_code="more_details")
    fake_provider.close=lambda:None
    monkeypatch.setattr("src.controller.GeminiProvider",lambda *a,**k:fake_provider)
    monkeypatch.setenv("GEMINI_API_KEY","dummy")
    app.run()
    app.checkbox(key="use_ai").set_value(True).run()
    submit(app)
    assert not app.exception
    assert any("Please add a learning goal" in message.value for message in app.info)
    assert not any("AI explanation available" in message.value for message in app.caption)
    assert not any(button.key and button.key.startswith("complete_") for button in app.button)


def test_live_sources_run_on_submission_and_render_the_active_catalog(app, monkeypatch):
    from datetime import datetime, timezone
    from src.sources import CatalogRefresh

    calls = []
    def refresh(catalog, profile, **kwargs):
        calls.append(profile.career_id)
        active = catalog.model_copy(deep=True)
        next(r for r in active.records if r.code == "ECE101").title = "Live HTTP fixture programming"
        source = next(s for s in active.sources if s.source_id == "catalog:ECE101")
        source.last_checked_at = datetime(2026, 11, 4, 3, tzinfo=timezone.utc)
        source.verification_status = "verified"
        return CatalogRefresh(active)

    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.run()
    assert calls == []
    submit(app)
    assert not app.exception and calls == ["ai_ml"]
    assert any("Live HTTP fixture programming" in item.value for item in app.markdown)
    assert any("Checked 2026-11-03 20:00 MST" in item.value for item in app.caption)
    app.run()
    assert calls == ["ai_ml"]
    app.selectbox(key="career_id").set_value("embedded")
    submit(app)
    assert not app.exception and calls == ["ai_ml", "embedded"]


def test_changed_prerequisite_replaces_approval_in_cards_and_inspector(app, monkeypatch):
    from src.sources import CatalogRefresh

    changed = False
    def refresh(catalog, profile, **kwargs):
        active = catalog.model_copy(deep=True)
        course = next(r for r in active.records if r.code == "CSC120")
        proof = course.rule_evidence[0]
        course.rule_verification = proof.verification_status = "changed" if changed else "verified"
        if changed:
            proof.observed_text = "Changed fixture statement awaiting review."
        for source in active.sources:
            if source.source_id in course.source_ids:
                source.verification_status = "verified"
        return CatalogRefresh(active)

    monkeypatch.setattr("src.controller.refresh_catalog", refresh)
    monkeypatch.setenv("ECE_REFRESH_SOURCES", "true")
    app.text_area(key="course_text").set_value("ECE101:B")
    submit(app)
    open_inspector(app)
    assert not app.exception
    assert any("Recorded prerequisites satisfied" in caption.value for caption in app.caption)
    changed = True
    submit(app)
    assert not app.exception
    assert not any("Recorded prerequisites satisfied" in caption.value for caption in app.caption)
    assert any("Enrollment requirements unverified" in caption.value for caption in app.caption)
    assert any("prerequisite evidence or interpretation needs review" in item.value for item in app.markdown)
    assert any("Changed fixture statement awaiting review." in item.value for item in app.text)
    assert any("uofa:CSC120:2026-2027:rule:R1299-L40" in item.value for item in app.markdown)


def test_discovered_sources_reach_collection_picker_and_trace(app, monkeypatch, catalog, tmp_path):
    from src.discovery import load_discovery_plans
    from src.models import Record
    from src.sources import refresh_catalog
    from test_discovery import CS_ID, ECE_IDS, client_for

    plans = load_discovery_plans()
    new_courses = {identity: Record(record_id="fixture:" + code, kind="course", code=code,
        title="Discovered fixture " + code, summary="Fixture programming and hardware.", credits=3,
        source_ids=["fixture"], catalog_version="2026-2027")
        for identity, code in zip([*ECE_IDS, CS_ID],
                                  ['ECE175', 'ECE275', 'ECE274A', 'CSC110'])}
    seen = []
    def refresh(catalog, profile, **kwargs):
        assert len(kwargs.pop('discovery_plans')) == 2
        with client_for(catalog, plans, new_courses, seen=seen) as client:
            return refresh_catalog(catalog, profile, client=client, discovery_plans=plans,
                                   cache_dir=tmp_path / 'sources')
    monkeypatch.setattr('src.controller.refresh_catalog', refresh)
    monkeypatch.setenv('ECE_REFRESH_SOURCES', 'true')
    submit(app)
    assert not app.exception
    assert any('8 courses' in caption.value for caption in app.caption)
    assert any('Discovered fixture CSC110' in item.label for item in app.expander)
    assert len(app.session_state['result'].trace['source_refresh']['discovered_courses']) == 3
    calls = len(seen)
    app.run()
    assert len(seen) == calls
    assert any(option.startswith('CSC110 · ') for option in app.multiselect(key='completed_courses').options)


def test_resource_sources_render_versions_and_update_only_on_submission(app, monkeypatch, tmp_path):
    import httpx
    from src.sources import refresh_catalog
    from src.resource_sources import RESOURCE_URLS
    from test_resource_sources import INTRO, resource_page

    changed = False
    seen = []
    def respond(request):
        url = str(request.url)
        seen.append(url)
        rid = next((rid for rid, known in RESOURCE_URLS.items() if known == url), None)
        if rid is None:
            return httpx.Response(503)
        intro = 'Changed fixture resource introduction describes updated programming examples and study material.' if changed else INTRO
        return httpx.Response(200, text=resource_page(rid, intro=intro), headers={'Content-Type': 'text/html'})
    def refresh(catalog, profile, **kwargs):
        assert kwargs['resource_checks'] is True
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return refresh_catalog(catalog, profile, client=client, resource_checks=True,
                                   cache_dir=tmp_path / 'sources')
    monkeypatch.setattr('src.controller.refresh_catalog', refresh)
    monkeypatch.setenv('ECE_REFRESH_SOURCES', 'true')
    submit(app)
    assert not app.exception
    assert any(INTRO in item.value for item in app.markdown)
    assert any('Version: 2.99.0+fixture' in item.value for item in app.caption)
    assert app.session_state['result'].trace['resource_versions']['resource:cs50'] == '2026'
    count = len(seen)
    app.run()
    assert len(seen) == count
    changed = True
    submit(app)
    assert not app.exception
    assert any('Changed fixture resource introduction' in item.value for item in app.markdown)
