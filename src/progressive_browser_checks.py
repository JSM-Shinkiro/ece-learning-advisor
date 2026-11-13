"""Controlled source and provider waits against the real student UI and WebSocket."""

import json
from pathlib import Path
import tempfile
import time
import traceback
from urllib.parse import urlsplit

from .browser_checks import browser_url


def run_progressive_browser_checks(url,control,*,executable_path=None,timeout_ms=20000,diagnostics_dir=None):
    report={"passed":False,"mode":"controlled_provider_local_ui","checks":[],
        "limits":["Provider outputs and delays are controlled fixtures; no live AI quality or latency is measured.",
                  "Source refreshes use bundled data with controlled check metadata and wait events.",
                  "The helper blocks all server-side external HTTP calls.",
                  "This checks one local browser session, not public hosting or participant usability."]}
    stage="browser_startup";started=time.monotonic()
    counts={"full_runs":0,"fragment_runs":0,"page_errors":0,"stream_connections":0}
    def passed(detail,begin):
        report["checks"].append({"name":stage,"passed":True,"detail":detail,"seconds":round(time.monotonic()-begin,3)})
    try:
        from playwright.sync_api import sync_playwright,expect
        from google.protobuf.message import DecodeError
        from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
        url=browser_url(url);origin=urlsplit(url);control=Path(control)
        with tempfile.TemporaryDirectory(prefix="ece-progressive-downloads-") as temporary,sync_playwright() as driver:
            browser=driver.chromium.launch(executable_path=executable_path)
            try:
                context=browser.new_context(accept_downloads=True,viewport={"width":1500,"height":1100})
                def route(request):
                    target=urlsplit(request.request.url)
                    if (target.scheme,target.netloc)==(origin.scheme,origin.netloc):request.continue_()
                    else:request.abort()
                context.route("**/*",route)
                page=context.new_page();page.set_default_timeout(timeout_ms)
                page.on("pageerror",lambda _:counts.update(page_errors=counts["page_errors"]+1))
                def websocket(stream):
                    if urlsplit(stream.url).path != origin.path+"_stcore/stream":return
                    counts["stream_connections"]+=1
                    def received(raw):
                        if not isinstance(raw,bytes):return
                        message=ForwardMsg()
                        try:message.ParseFromString(raw)
                        except DecodeError:return
                        if message.WhichOneof("type")=="script_finished":
                            if message.script_finished==0:counts["full_runs"]+=1
                            elif message.script_finished==3:counts["fragment_runs"]+=1
                    stream.on("framereceived",received)
                page.on("websocket",websocket)
                def wait_until(predicate):
                    deadline=time.monotonic()+timeout_ms/1000
                    while not predicate() and time.monotonic()<deadline:page.wait_for_timeout(50)
                    assert predicate()
                def expand(label):
                    summary=page.locator("summary").filter(has=page.get_by_text(label,exact=True))
                    if summary.locator("..").get_attribute("open") is None:summary.click()
                def navigate(label):
                    page.get_by_test_id("stButtonGroup").get_by_text(label, exact=True).click()
                def pick_record(label, value):
                    field = page.get_by_role("combobox", name=label, exact=True)
                    field.fill(value)
                    page.get_by_role("option", name=value, exact=True).click()
                    field.press("Escape")
                def choose(label,value):
                    field=page.get_by_role("combobox",name=label,exact=True)
                    field.scroll_into_view_if_needed();field.focus();field.press("Escape")
                    page.get_by_test_id("stSelectbox").filter(has=field).get_by_role("button",name="Open",exact=True).click()
                    page.get_by_role("option",name=value,exact=True).click()
                    expect(field).to_have_value(value)
                def submit(question):
                    page.get_by_role("textbox",name="A question about your next step",exact=True).fill(question)
                    button=page.get_by_role("button",name="Update my roadmap",exact=True)
                    button.focus();button.click()
                def source_plan(case):
                    expect(page.get_by_text("Source plan ready · AI assistance is still running",exact=True)).to_be_visible()
                    expect(page.get_by_role("button",name="Mark completed",exact=True).first).to_be_visible()
                    wait_until(lambda:(control/(case+".started")).exists())
                    assert not (control/(case+".closed")).exists()
                def release(case):
                    (control/(case+".release")).touch()
                    wait_until(lambda:(control/(case+".closed")).exists())
                def export(name):
                    expand("Saved profile")
                    with page.expect_download() as download:
                        page.get_by_role("button",name="Download my profile",exact=True).click()
                    path=Path(temporary)/name;download.value.save_as(path)
                    return json.loads(path.read_text())
                ai_caption=page.get_by_text("AI explanation available · based on selected sources",exact=True)
                page.goto(url,wait_until="domcontentloaded")
                stage="beginner_landing";begin=time.monotonic()
                expect(page.get_by_role("heading",name="Learn how an ECE advisor finds evidence",exact=True)).to_be_visible()
                expect(page.get_by_role("heading",name="Learning roadmap",exact=True)).to_be_visible()
                expect(page.get_by_label("Question to evidence flowchart")).to_be_visible()
                expect(page.get_by_role("button",name="Update my roadmap",exact=True)).to_have_count(0)
                image=page.get_by_test_id("stImage").locator("img")
                expect(image).to_be_visible()
                page.wait_for_function("Array.from(document.images).some(img => img.complete && img.naturalWidth > 0)")
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir)/"learning-beginner.png"))
                page.set_viewport_size({"width":390,"height":844})
                page.wait_for_function("window.innerWidth === 390")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir)/"learning-mobile.png"))
                page.set_viewport_size({"width":1500,"height":1100})
                page.get_by_text("The official requirements and my completed coursework",exact=True).click()
                expect(page.get_by_text("Correct. A relevance score helps you find a course.",exact=False)).to_be_visible()
                passed("The illustrated landing page fits phone width and gives immediate feedback on preparation versus relevance.",begin)

                stage="intermediate_experiment";begin=time.monotonic()
                page.get_by_role("button",name="Try a preset experiment",exact=True).click()
                expect(page.get_by_role("heading",name="Intermediate · Apply & analyze",exact=True)).to_be_visible()
                expect(page.get_by_test_id("stPlotlyChart")).to_be_visible()
                ranking=page.locator('[data-ece-ranking="html"]')
                expect(ranking).to_contain_text("Keyword ranking score")
                choose("Ranking method","Topic cosine")
                expect(ranking).to_contain_text("Topic cosine ranking score")
                expand("Inspect evidence")
                expect(page.get_by_text("product of lengths", exact=False)).to_be_visible()
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir)/"learning-intermediate.png"))
                expand("Developer view · visualization code")
                expect(page.get_by_test_id("stCode").first).to_contain_text("def plot_experiment")
                passed("A preset changes ranking method and shows the live plot and its actual source code without AI.",begin)

                stage="advanced_comparison";begin=time.monotonic()
                page.get_by_role("button",name="Create your variation",exact=True).click()
                expect(page.get_by_role("heading",name="Advanced · Evaluate & create",exact=True)).to_be_visible()
                expect(page.get_by_role("combobox", name="Comparison preset", exact=True)).to_have_value("Program a sensor")
                expect(page.get_by_role("combobox", name="Variation ranking method", exact=True)).to_have_value("Topic cosine")
                choose("Variation ranking method", "Hybrid")
                question = "How do I train a neural network for image classification in Python?"
                page.get_by_role("textbox",name="Your variation",exact=True).fill(question)
                pick_record("Expected useful records", "ECE425")
                page.get_by_role("button",name="Compare with preset",exact=True).click()
                expect(page.get_by_role("heading",name="Your comparison",exact=True)).to_be_visible()
                metrics=page.get_by_test_id("stMetricValue")
                expect(metrics.nth(0)).to_have_text("0 / 1")
                expect(metrics.nth(1)).to_have_text("1 / 1")
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir)/"learning-advanced.png"))
                choose("Record to explain", "ECE425")
                choose("How did this record move?", "Entered the ranking")
                expand("Inspect evidence for this record")
                observation = page.get_by_role("textbox", name="What in the evidence explains the result?", exact=True)
                explanation = "ECE425 covers neural networks relevant to image classification."
                observation.fill(explanation)
                observation.press("Tab")
                page.get_by_role("button",name="Save my observation",exact=True).click()
                with page.expect_download() as comparison:
                    page.get_by_role("button",name="Download my comparison",exact=True).click()
                comparison_path=Path(temporary)/"comparison.json"
                comparison.value.save_as(comparison_path)
                saved=json.loads(comparison_path.read_text(encoding="utf-8"))
                assert saved["expected_records"] == ["ECE425"] and saved["observation"] == explanation
                assert saved["observed_rank_change"] == "Entered the ranking"
                assert not (control/"provider.calls").exists()
                passed("A user question changes expected evidence in the top three and exports its saved observation.",begin)

                stage = "lesson_continuity"
                begin = time.monotonic()
                variation_input = page.get_by_role("textbox", name="Your variation", exact=True)
                variation_input.fill("How do I program in C?")
                navigate("Beginner")
                expect(page.get_by_role("heading", name="Learn how an ECE advisor finds evidence", exact=True)).to_be_visible()
                navigate("Advanced")
                expect(variation_input).to_have_value("How do I program in C?")
                expect(page.get_by_role("combobox", name="Variation ranking method", exact=True)).to_have_value("Hybrid")
                expect(page.get_by_text("Showing your last comparison.", exact=False)).to_be_visible()
                expect(page.get_by_text(question, exact=True)).to_be_visible()
                page.get_by_role("button", name="Use this question in Advisor", exact=True).click()
                expect(page.get_by_role("heading",name="Your next step, with a path forward.",exact=True)).to_be_visible()
                expect(page.get_by_role("textbox", name="A question about your next step", exact=True)).to_have_value(question)
                expect(page.get_by_text("Your lesson question is in Your starting point.", exact=False)).to_be_visible()
                assert export("lesson-draft.json")["question"] == ""
                passed("The unsubmitted variation survives navigation and the evaluated question opens as an Advisor draft.", begin)
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir) / "learning-advisor-draft.png"))

                stage = "saved_plan_during_source_checks"
                begin = time.monotonic()
                submit("ECE101 controlled source update")
                wait_until(lambda: (control / "source-update.started").exists())
                expect(page.get_by_text("Saved-data plan ready · checking official sources", exact=True)).to_be_visible()
                expect(page.get_by_role("button", name="Mark completed", exact=True).first).to_be_visible()
                assert not (control / "source-update.release").exists()
                assert not (control / "provider.calls").exists()
                saved_plan_ready_seconds = time.monotonic() - begin
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir) / "learning-saved-roadmap.png"))
                expand("How this plan was made")
                saved_timing = page.get_by_text("Saved-data plan built in", exact=False)
                expect(saved_timing).to_be_visible()
                draft = page.get_by_role("textbox", name="What interests you?", exact=True)
                draft.fill("Draft typed during source checks")
                release("source-update")
                expect(page.get_by_text("Learning suggestions from the available source evidence", exact=True)).to_be_visible()
                expect(page.get_by_text("Saved-data plan ready · checking official sources", exact=True)).to_have_count(0)
                expect(draft).to_have_value("Draft typed during source checks")
                assert not (control / "provider.calls").exists()
                expect(saved_timing).to_be_visible()
                passed("The saved plan is usable and the source update preserves the open inspector and an unsubmitted profile edit.", begin)
                report["saved_data_interaction"] = {"roadmap_controls_observed_seconds": round(saved_plan_ready_seconds, 3)}
                draft.fill("")

                stage = "keep_saved_plan"
                begin = time.monotonic()
                submit("ECE101 controlled keep saved plan")
                wait_until(lambda: (control / "source-keep.started").exists())
                expect(page.get_by_text("Saved-data plan ready · checking official sources", exact=True)).to_be_visible()
                expect(saved_timing).to_be_visible()
                page.get_by_role("button", name="Keep saved-data plan", exact=True).click()
                expect(page.get_by_text("Source checks stopped. Your saved-data plan is ready to use.", exact=True)).to_be_visible()
                release("source-keep")
                expect(page.get_by_text("Saved-data plan · based on dated course and resource snapshots", exact=True)).to_be_visible()
                expect(saved_timing).to_be_visible()
                assert not (control / "provider.calls").exists()
                passed("Keeping the dated plan removes the active update and excludes the released source result.", begin)

                stage = "lesson_embedding_comparison"
                begin = time.monotonic()
                wait_until(lambda:counts["full_runs"]>0)
                expand("AI and ranking options")
                checkbox=page.get_by_role("checkbox",name="Generate AI explanations",exact=True)
                expect(checkbox).to_be_enabled()
                before=counts["full_runs"]
                page.get_by_text("Generate AI explanations",exact=True).click()
                wait_until(lambda:counts["full_runs"]>before)
                submit(question)
                expect(ai_caption).to_be_visible()
                expand("How this plan was made")
                expand("Compare lesson and neural embeddings")
                expect(page.get_by_text("embedding dimensions from controlled-browser-vectors", exact=False)).to_be_visible()
                if diagnostics_dir is not None:
                    page.screenshot(path=str(Path(diagnostics_dir) / "learning-embedding-comparison.png"))
                passed("The carried question reaches the Advisor and compares both representations on its existing test vectors.", begin)

                stage="source_plan_before_ai";begin=time.monotonic()
                submit("ECE101 controlled draft request");source_plan("draft")
                passed("A usable source plan appears while the controlled provider is still blocked.",begin)

                stage="draft_retention";begin=time.monotonic()
                draft=page.get_by_role("textbox",name="What interests you?",exact=True)
                draft.fill("Draft typed while AI works")
                expect(draft).to_have_value("Draft typed while AI works")
                release("draft");expect(ai_caption).to_be_visible()
                expect(draft).to_have_value("Draft typed while AI works")
                passed("The form remains editable and retains its unsubmitted draft when AI completes.",begin)

                stage="newer_profile_wins";begin=time.monotonic()
                submit("ECE101 controlled old request");source_plan("old")
                choose("Career direction","Embedded Systems")
                submit("ECE372A controlled fast request");expect(ai_caption).to_be_visible()
                expect(page.get_by_text("Saved profile: Incoming · Embedded Systems · 0 completed courses · 0 currently taking",exact=True)).to_be_visible()
                assert not (control/"old.closed").exists()
                newer=export("newer.json")
                assert newer["career_id"]=="embedded" and newer["question"]=="ECE372A controlled fast request"
                release("old");page.wait_for_timeout(1200)
                assert export("after-old.json")==newer
                expect(ai_caption).to_be_visible()
                passed("A newer profile completes while the old provider waits; releasing the old response cannot replace it.",begin)

                stage="keep_source_plan";begin=time.monotonic()
                submit("ECE372A controlled stop request");source_plan("stop")
                page.get_by_role("button",name="Keep source plan",exact=True).click()
                expect(page.get_by_text("AI assistance stopped. Your source plan is ready to use.",exact=True)).to_be_visible()
                expect(ai_caption).to_have_count(0)
                expect(page.get_by_role("button",name="Mark completed",exact=True).first).to_be_visible()
                release("stop");page.wait_for_timeout(1200)
                expect(ai_caption).to_have_count(0)
                assert export("stopped.json")["question"]=="ECE372A controlled stop request"
                passed("Keeping the source plan stops result acceptance, retains the plan and rejects late AI output.",begin)

                stage="collection_filters";begin=time.monotonic()
                page.get_by_role("tab",name="Courses & Resources",exact=True).click()
                full_runs=counts["full_runs"]
                provider_calls=(control/"provider.calls").read_text()
                draft.fill("Unsubmitted collection draft")
                query=page.get_by_role("textbox",name="Search courses and resources",exact=True)
                fragment_runs=counts["fragment_runs"]
                query.fill("ece 372a");query.press("Enter")
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(page.get_by_text("Showing 1 of 28 courses and resources · local collection search",exact=True)).to_be_visible()
                result_panel=page.get_by_test_id("stExpander").filter(has=page.locator("summary").filter(has_text="ECE372A · "))
                expect(result_panel.get_by_role("link")).to_have_count(0)
                fragment_runs=counts["fragment_runs"];result_panel.locator("summary").click()
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(result_panel.get_by_text("University course · 4 credits · Catalog 2026-2027",exact=True)).to_be_visible()
                expect(result_panel.get_by_role("link")).not_to_have_count(0)
                fragment_runs=counts["fragment_runs"];choose("Type","Resources only")
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                fragment_runs=counts["fragment_runs"];choose("Direction","Embedded Systems")
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                fragment_runs=counts["fragment_runs"]
                query.fill("pico");query.press("Enter")
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(page.get_by_text("Showing 1 of 28 courses and resources · local collection search",exact=True)).to_be_visible()
                expect(page.locator("summary").filter(has_text="Raspberry Pi Pico C/C++ SDK")).to_be_visible()
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                expect(draft).to_have_value("Unsubmitted collection draft")
                passed("Course-code, type and direction filters update locally; opening details keeps source metadata and triggers no advisor run.",begin)

                stage="mobile_collection";begin=time.monotonic()
                # Collapse while the desktop control is stable. Resizing first can
                # auto-collapse it between is_visible() and Playwright's click.
                sidebar=page.get_by_test_id("stSidebar")
                sidebar.hover()
                page.get_by_role("button",name="Collapse sidebar",exact=True).click()
                expect(sidebar).to_have_attribute("data-collapsed","true")
                page.set_viewport_size({"width":390,"height":844})
                expect(sidebar).to_have_attribute("data-collapsed","true")
                page.get_by_role("tab",name="Courses & Resources",exact=True).click()
                expect(query).to_have_value("pico")
                expect(page.get_by_role("combobox",name="Type",exact=True)).to_have_value("Resources only")
                fragment_runs=counts["fragment_runs"]
                query.fill("impossible-collection-match");query.press("Enter")
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(page.get_by_text("No courses or resources match these filters. Try a broader search or reset the filters.",exact=True)).to_be_visible()
                fragment_runs=counts["fragment_runs"];page.get_by_role("button",name="Reset filters",exact=True).click()
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(query).to_have_value("")
                expect(page.get_by_text("Showing 28 of 28 courses and resources · local collection search",exact=True)).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                passed("Filters and reset work at a 390-pixel phone width without horizontal page overflow or a full-app request.",begin)

                stage="mobile_inspector";begin=time.monotonic()
                page.get_by_role("tab",name="My Roadmap",exact=True).click()
                inspector_summary = page.locator("summary").filter(
                    has=page.get_by_text("How this plan was made", exact=True))
                expect(inspector_summary).to_be_visible()
                ranking = page.locator('[data-ece-ranking="html"]')
                if inspector_summary.locator("..").get_attribute("open") is not None:
                    inspector_summary.click()
                expect(ranking).to_have_count(0)
                fragment_runs=counts["fragment_runs"]
                inspector_summary.click()
                wait_until(lambda:counts["fragment_runs"]>fragment_runs)
                expect(ranking).to_be_visible()
                expect(page.get_by_test_id("stPlotlyChart")).to_have_count(0)
                expect(page.get_by_role("button",name="Download request trace",exact=True)).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                if diagnostics_dir is not None:
                    ranking.screenshot(path=str(Path(diagnostics_dir)/"ranking-mobile.png"))
                passed("Native ranking and trace download fit a 390-pixel phone viewport without a full app or provider request.",begin)
                page.set_viewport_size({"width":1500,"height":1100})
                if diagnostics_dir is not None:
                    ranking.screenshot(path=str(Path(diagnostics_dir)/"ranking-desktop.png"))

                stage="posting_progress";begin=time.monotonic()
                page.get_by_role("tab",name="Opportunities",exact=True).click()
                page.get_by_role("button",name="Available Opportunities",exact=True).click()
                expect(page.get_by_text("Controlled Embedded Intern",exact=True)).to_be_visible()
                check_button=page.get_by_role("button",name="Check posting details",exact=True)
                check_button.click()
                wait_until(lambda:(control/"posting.started").exists())
                expect(page.get_by_text("Checking posting details...",exact=True)).to_be_visible()
                (control/"posting.release").touch()
                description=page.get_by_text("Controlled posting description: embedded programming practice.",exact=True)
                expect(description).to_be_visible()
                assert len((control/"opportunity_search.calls").read_text().splitlines())==1
                assert len((control/"posting_detail.calls").read_text().splitlines())==1
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                passed("A deliberately delayed detail request shows feedback beside the selected listing and does not rerun the roadmap.",begin)

                stage="posting_failure_retains_search";begin=time.monotonic()
                check_button.click()
                expect(page.get_by_text("This posting could not be reached. Its requirements have not been checked.",exact=True)).to_be_visible()
                expect(description).to_have_count(0)
                expect(page.get_by_text("Controlled Embedded Intern",exact=True)).to_be_visible()
                assert len((control/"opportunity_search.calls").read_text().splitlines())==1
                assert len((control/"posting_detail.calls").read_text().splitlines())==2
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                passed("A failed recheck clears verified content while retaining the saved search; neither search nor AI is repeated.",begin)

                stage="ece_catalog_local_paging";begin=time.monotonic()
                page.get_by_role("tab",name="Courses & Resources",exact=True).click()
                page.get_by_text("All undergraduate ECE courses",exact=True).click()
                expect(page.get_by_text("Effective-date filter 2027-01-13", exact=False)).to_be_visible()
                expect(page.get_by_text("78 matching courses · Page 1 of 6 · local catalog search",exact=True)).to_be_visible()
                catalog_panels=page.get_by_test_id("stExpander").filter(has=page.locator("summary").filter(has_text="ECE"))
                expect(catalog_panels).to_have_count(15)
                assert all(catalog_panels.nth(i).get_by_role("link").count()==0 for i in range(15))
                page.get_by_role("button",name="Next courses",exact=True).click()
                expect(page.get_by_text("78 matching courses · Page 2 of 6 · local catalog search",exact=True)).to_be_visible()
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                passed("All 78 catalog courses are locally paged in groups of 15; closed panels omit details and paging makes no advisor call.",begin)

                stage = "ece_enrollment_references"
                begin = time.monotonic()
                catalog_query = page.get_by_role("textbox", name="Search the ECE catalog", exact=True)
                catalog_query.fill("ECE 101")
                catalog_query.press("Enter")
                expect(page.get_by_text("1 matching courses · Page 1 of 1 · local catalog search", exact=True)).to_be_visible()
                expand("ECE101 · Programming 1")
                expect(page.get_by_text("The department lists MATH 112", exact=False)).to_be_visible()
                expect(page.get_by_text("The 2026–27 advised plan lists completion", exact=False)).to_be_visible()
                expect(page.get_by_text("Catalog record effective from 2026-01-01 · enrollment requirements unverified", exact=True)).to_be_visible()
                expect(page.get_by_role("link", name="Open class search", exact=True)).to_have_attribute(
                    "href", "https://studentcenter.arizona.edu/app/ui/public/select-campus")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                assert counts["full_runs"] == full_runs and (control / "provider.calls").read_text() == provider_calls
                passed("The phone directory displays both ECE101 references and the class-search link without an advisor request.", begin)

                stage="ece_catalog_variable_credit_phone";begin=time.monotonic()
                catalog_query.fill("ece 493");catalog_query.press("Enter")
                expect(page.get_by_text("1 matching courses · Page 1 of 1 · local catalog search",exact=True)).to_be_visible()
                expand("ECE493 · Internship")
                expect(page.get_by_text("1–12 credits · Catalog 2026-2027",exact=True)).to_be_visible()
                expect(page.get_by_role("link",name="Official course page",exact=True)).to_have_attribute("href","https://catalog.arizona.edu/courses/0122191")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                assert counts["full_runs"]==full_runs and (control/"provider.calls").read_text()==provider_calls
                passed("Exact spaced-code search resets pagination and shows the official variable-credit range without phone overflow or advisor work.",begin)

                stage="ece_catalog_requested_roadmap";begin=time.monotonic()
                catalog_query.fill("ECE413");catalog_query.press("Enter")
                expect(page.locator("summary").filter(has_text="ECE413 · ")).to_be_visible()
                page.locator("summary").filter(has_text="ECE413 · ").click()
                page.get_by_role("button",name="Explore ECE413 in my roadmap",exact=True).click()
                page.get_by_role("tab",name="My Roadmap",exact=True).click()
                expect(page.get_by_role("heading",name="Explore requested courses",exact=True)).to_be_visible()
                expect(page.get_by_text("Requested catalog course · preparation level and career connection unreviewed",exact=True)).to_be_visible()
                expect(ai_caption).to_be_visible()
                assert len((control/"provider.calls").read_text().splitlines())==len(provider_calls.splitlines())+1
                passed("An explicit catalog action creates a source-grounded course card with unreviewed preparation and enrollment, using one controlled advisor request.",begin)

                stage="browser_health";begin=time.monotonic()
                assert counts["stream_connections"]==1 and counts["page_errors"]==0 and counts["fragment_runs"]>0
                report["protocol_counts"]=counts
                report["browser"]={"engine":"chromium","version":browser.version}
                passed("The real Streamlit session exchanges full and fragment updates with no JavaScript errors.",begin)
                report["passed"]=True
            finally:browser.close()
    except Exception as exc:
        lines=[frame.lineno for frame in traceback.extract_tb(exc.__traceback__) if Path(frame.filename).name==Path(__file__).name]
        report["checks"].append({"name":stage,"passed":False,"detail":"The controlled progressive browser gate did not complete.",
                                  "error_type":type(exc).__name__,"failure_line":lines[-1] if lines else None})
    report["seconds"]=round(time.monotonic()-started,3)
    return report
