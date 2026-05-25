from datetime import date

from eol_checker.constants import JIRA_URL
from eol_checker.utils import get_jira_ticket_url, get_lifecycles, is_eol_version


def test_is_eol_version_same_month_returns_one():
    today = date(2025, 5, 15)
    enddate = date(2025, 5, 1)
    assert is_eol_version(enddate, today) == 1


def test_is_eol_version_next_month_returns_two():
    today = date(2025, 5, 15)
    enddate = date(2025, 6, 1)
    assert is_eol_version(enddate, today) == 2


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
