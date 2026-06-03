import os
from datetime import date

from eol_checker.constants import JIRA_URL
from eol_checker.utils import (
    get_env_variable,
    get_jira_ticket_url,
    get_lifecycles,
    is_eol_version,
    load_mails_from_environment,
)


def test_is_eol_version_same_month_returns_one():
    today = date(2025, 5, 15)
    enddate = date(2025, 5, 1)
    assert is_eol_version(enddate, today) == 1


def test_is_eol_version_next_month_returns_two():
    today = date(2025, 5, 15)
    enddate = date(2025, 6, 1)
    assert is_eol_version(enddate, today) == 2


def test_is_eol_version_previous_month_returns_three():
    today = date(2025, 5, 15)
    enddate = date(2025, 4, 1)
    assert is_eol_version(enddate, today) == 3


def test_is_eol_version_other_month_returns_zero():
    today = date(2025, 5, 15)
    enddate = date(2025, 7, 1)
    assert is_eol_version(enddate, today) == 0


def test_is_eol_version_different_year_returns_zero():
    today = date(2025, 5, 15)
    enddate = date(2026, 5, 1)
    assert is_eol_version(enddate, today) == 0


def test_get_lifecycles_returns_lifecycles_from_dict():
    data = {"lifecycles": [{"name": "nodejs", "eol": "2025-01-01"}]}
    assert list(get_lifecycles(data)) == data["lifecycles"]


def test_get_lifecycles_returns_empty_when_key_missing():
    assert list(get_lifecycles({"other": []})) == []


def test_get_lifecycles_returns_empty_for_non_dict():
    assert list(get_lifecycles([])) == []
    assert list(get_lifecycles(None)) == []


def test_get_jira_ticket_url_builds_browse_link():
    issue_id = "RHELMISC-12345"
    assert get_jira_ticket_url(issue_id) == f"{JIRA_URL}/browse/{issue_id}"


def test_get_env_variable_returns_split_list(monkeypatch):
    monkeypatch.setenv("TEST_EMAILS", "a@redhat.com,b@redhat.com")

    assert get_env_variable("TEST_EMAILS") == ["a@redhat.com", "b@redhat.com"]


def test_get_env_variable_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)

    assert get_env_variable("MISSING_VAR") == []


def test_get_env_variable_returns_default_when_empty(monkeypatch):
    monkeypatch.setenv("EMPTY_VAR", "")

    assert get_env_variable("EMPTY_VAR", "fallback@redhat.com") == []


def test_load_mails_from_environment(monkeypatch):
    monkeypatch.setenv("DB_EMAILS", "db@redhat.com")
    monkeypatch.setenv("NODEJS_EMAILS", "node@redhat.com")
    monkeypatch.delenv("RUBY_EMAILS", raising=False)

    mails = load_mails_from_environment()

    assert mails["mariadb"] == ["db@redhat.com"]
    assert mails["mysql"] == ["db@redhat.com"]
    assert mails["postgresql"] == ["db@redhat.com"]
    assert mails["nodejs"] == ["node@redhat.com"]
    assert mails["ruby"] == []
