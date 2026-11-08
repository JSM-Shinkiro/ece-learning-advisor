"""Reproduce the reported timing failure and prevent misleading CI success summaries."""

import copy
import json
from pathlib import Path
import sys

import pytest

from scripts.summarize_browser_ci import REPORTS, build_summary, main, report_status

EVIDENCE = Path(__file__).resolve().parents[1] / 'docs/evidence/lightweight_inspector_2026-11-07.json'


@pytest.fixture
def evidence():
    return json.loads(EVIDENCE.read_text())


def write_reports(directory, reports):
    for _, name, _ in REPORTS:
        (directory/name).write_text(json.dumps(reports[name]))


def test_actual_successful_ci_reports_produce_five_distinct_passing_rows(tmp_path, evidence):
    write_reports(tmp_path,evidence['verified_ci']['browser']['reports'])
    summary,passed=build_summary(tmp_path,revision='a'*40,run_id='123')
    assert passed and summary.count('**PASS**')==5
    assert '10/10 checks passed' in summary and '6/6 checks passed' in summary
    assert '686.7 ms median' in summary and '1608.4 ms median' in summary
    assert 'commit/'+'a'*40 in summary and 'actions/runs/123' in summary


def test_actual_reported_failure_separates_green_acceptance_from_incomplete_timings(tmp_path, evidence):
    write_reports(tmp_path,evidence['initial_ci']['browser']['reports'])
    summary,passed=build_summary(tmp_path)
    assert not passed and summary.count('**PASS**')==3 and summary.count('**FAIL**')==2
    assert '0/5 sessions complete; failed stage: Inspector reopening (5)' in summary
    assert '686.7' not in summary


@pytest.mark.parametrize('change',[{'passed':True,'successful_samples':0},
    {'passed':True,'samples':[]},{'successful_samples':True},
    {'summary_ms':{}},{'version':'different-boundary'},
    {'summary_ms':{'inspector_first_ready_ms':{'n':5,'median':float('nan')}}}])
def test_inconsistent_or_unidentified_timing_cannot_be_reported_as_success(change, evidence):
    report=copy.deepcopy(evidence['verified_ci']['browser']['reports']['browser-performance.json'])
    report.update(change)
    assert report_status(report,'timing')[0]=='INVALID'


def test_success_flag_cannot_override_failed_check_rows():
    assert report_status({'passed':True,'checks':[{'passed':False}]},'checks')[0]=='INVALID'
    assert report_status({'passed':True,'checks':[]},'checks')[0]=='INVALID'


def test_missing_and_malformed_reports_are_named_without_leaking_their_contents(tmp_path, evidence):
    write_reports(tmp_path,evidence['verified_ci']['browser']['reports'])
    (tmp_path/'reviewer-browser.json').unlink()
    (tmp_path/'browser-performance.json').write_text('private-profile-and-error')
    summary,passed=build_summary(tmp_path,revision='private-key',run_id='private-run')
    assert not passed and '**MISSING**' in summary and '**INVALID**' in summary
    assert 'private' not in summary


def test_freeform_errors_and_unknown_stages_never_enter_summary(tmp_path, evidence):
    reports=copy.deepcopy(evidence['initial_ci']['browser']['reports'])
    for sample in reports['browser-performance.json']['samples']:
        sample['failure']={'stage':'private-profile','error_type':'private-exception','message':'private-token'}
    write_reports(tmp_path,reports)
    summary,_=build_summary(tmp_path)
    assert 'Other stage (5)' in summary and 'private' not in summary


def test_summary_saves_artifact_and_appends_to_github_without_replacing_existing_text(tmp_path, evidence, monkeypatch):
    write_reports(tmp_path,evidence['verified_ci']['browser']['reports'])
    output=tmp_path/'summary.md';github=tmp_path/'github.md';github.write_text('Existing job note\n')
    monkeypatch.setenv('GITHUB_STEP_SUMMARY',str(github))
    monkeypatch.setattr(sys,'argv',['summarize_browser_ci.py','--reports-dir',str(tmp_path),
        '--output',str(output),'--github-summary'])
    assert main()==0 and output.read_text() in github.read_text()
    assert github.read_text().startswith('Existing job note\n')
    before=github.read_text();assert main()==1
    assert github.read_text()==before


def test_incomplete_reports_fail_the_summary_command_and_keep_diagnostic_artifact(tmp_path, evidence, monkeypatch, capsys):
    write_reports(tmp_path,evidence['initial_ci']['browser']['reports'])
    output=tmp_path/'summary.md'
    monkeypatch.setattr(sys,'argv',['summarize_browser_ci.py','--reports-dir',str(tmp_path),'--output',str(output)])
    assert main()==1 and output.exists()
    assert '::error title=Browser reports incomplete::' in capsys.readouterr().out
