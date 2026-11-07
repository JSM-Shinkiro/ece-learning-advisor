"""Controlled slow-provider checks against the real student UI and WebSocket."""

import json
from pathlib import Path
import tempfile
import time
import traceback
from urllib.parse import urlsplit

from .browser_checks import browser_url


def run_progressive_browser_checks(url,control,*,executable_path=None,timeout_ms=20000):
    report={"passed":False,"mode":"controlled_provider_local_ui","checks":[],
        "limits":["Provider outputs and delays are controlled fixtures; no live AI quality or latency is measured.",
                  "Sources are dated bundled snapshots; the helper blocks all server-side HTTP calls.",
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
                def choose(label,value):
                    field=page.get_by_role("combobox",name=label,exact=True)
                    field.scroll_into_view_if_needed();field.focus();field.press("Escape")
                    page.get_by_test_id("stSelectbox").filter(has=field).get_by_role("button",name="Open",exact=True).click()
                    page.get_by_role("option",name=value,exact=True).click()
                    expect(field).to_have_value(value)
                def submit(question):
                    expand("Optional details")
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
                expect(page.get_by_role("heading",name="Your next step, with a path forward.",exact=True)).to_be_visible()
                wait_until(lambda:counts["full_runs"]>0)
                expand("AI and ranking options")
                checkbox=page.get_by_role("checkbox",name="Generate AI explanations",exact=True)
                expect(checkbox).to_be_enabled()
                before=counts["full_runs"]
                page.get_by_text("Generate AI explanations",exact=True).click()
                wait_until(lambda:counts["full_runs"]>before)

                stage="source_plan_before_ai";begin=time.monotonic()
                submit("Controlled draft request");source_plan("draft")
                passed("A usable source plan appears while the controlled provider is still blocked.",begin)

                stage="draft_retention";begin=time.monotonic()
                draft=page.get_by_role("textbox",name="What interests you?",exact=True)
                draft.fill("Draft typed while AI works")
                expect(draft).to_have_value("Draft typed while AI works")
                release("draft");expect(ai_caption).to_be_visible()
                expect(draft).to_have_value("Draft typed while AI works")
                passed("The form remains editable and retains its unsubmitted draft when AI completes.",begin)

                stage="newer_profile_wins";begin=time.monotonic()
                submit("Controlled old request");source_plan("old")
                choose("Career direction","Embedded Systems")
                submit("Controlled fast request");expect(ai_caption).to_be_visible()
                expect(page.get_by_text("Saved profile: Incoming · Embedded Systems · 0 completed courses · 0 currently taking",exact=True)).to_be_visible()
                assert not (control/"old.closed").exists()
                newer=export("newer.json")
                assert newer["career_id"]=="embedded" and newer["question"]=="Controlled fast request"
                release("old");page.wait_for_timeout(1200)
                assert export("after-old.json")==newer
                expect(ai_caption).to_be_visible()
                passed("A newer profile completes while the old provider waits; releasing the old response cannot replace it.",begin)

                stage="keep_source_plan";begin=time.monotonic()
                submit("Controlled stop request");source_plan("stop")
                page.get_by_role("button",name="Keep source plan",exact=True).click()
                expect(page.get_by_text("AI assistance stopped. Your source plan is ready to use.",exact=True)).to_be_visible()
                expect(ai_caption).to_have_count(0)
                expect(page.get_by_role("button",name="Mark completed",exact=True).first).to_be_visible()
                release("stop");page.wait_for_timeout(1200)
                expect(ai_caption).to_have_count(0)
                assert export("stopped.json")["question"]=="Controlled stop request"
                passed("Keeping the source plan stops result acceptance, retains the plan and rejects late AI output.",begin)

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
