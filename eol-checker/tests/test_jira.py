import pytest
from flexmock import flexmock

from eol_checker import jira as jira_module
from eol_checker.constants import ALLOWED_STATUSES, JIRA_DEPRECATION_TICKET, JIRA_URL
from eol_checker.jira import JiraFetcher


@pytest.fixture
def fetcher():
    return JiraFetcher()


def test_init_uses_defaults_when_env_unset(monkeypatch):
    monkeypatch.delenv("JIRA_DEPRECATION_TICKET", raising=False)
    monkeypatch.delenv("JIRA_URL", raising=False)

    instance = JiraFetcher()

    assert instance.jira_deprecation_ticket == JIRA_DEPRECATION_TICKET
    assert instance.jira_url == JIRA_URL
    assert instance.jira_details is None
    assert instance.jira_deprecated_opened_issues == []


def test_init_uses_env_overrides(monkeypatch):
    monkeypatch.setenv("JIRA_DEPRECATION_TICKET", "CUSTOM-1")
    monkeypatch.setenv("JIRA_URL", "https://jira.example.com")

    instance = JiraFetcher()

    assert instance.jira_deprecation_ticket == "CUSTOM-1"
    assert instance.jira_url == "https://jira.example.com"


def test_jira_property_creates_client_once(fetcher):
    mock_client = flexmock()
    flexmock(jira_module).should_receive("Jira").once().and_return(mock_client)

    assert fetcher.jira is mock_client
    assert fetcher.jira is mock_client


def test_get_jira_deprecation_details_stores_issuelinks(fetcher):
    mock_client = flexmock()
    mock_client.should_receive("issue").with_args(
        fetcher.jira_deprecation_ticket
    ).and_return({"fields": {"issuelinks": [{"inwardIssue": {"key": "CLONE-1"}}]}})
    flexmock(jira_module).should_receive("Jira").and_return(mock_client)

    fetcher.get_jira_deprecation_details()

    assert fetcher.jira_details == [{"inwardIssue": {"key": "CLONE-1"}}]


def test_get_jira_deprecation_details_skips_when_no_issuelinks(fetcher):
    mock_client = flexmock()
    mock_client.should_receive("issue").with_args(
        fetcher.jira_deprecation_ticket
    ).and_return({"fields": {}})
    flexmock(jira_module).should_receive("Jira").and_return(mock_client)

    fetcher.get_jira_deprecation_details()

    assert fetcher.jira_details is None


def test_is_jira_filled_for_container_returns_matching_issue_id(fetcher):
    fetcher.jira_deprecated_opened_issues = [
        {
            "summary": "EOL nodejs RHEL9",
            "jira_issue_id": "RHELMISC-100",
            "issue_status": "Open",
        },
        {
            "summary": "EOL httpd RHEL9",
            "jira_issue_id": "RHELMISC-101",
            "issue_status": "Open",
        },
    ]

    assert fetcher.is_jira_filled_for_container("nodejs") == "RHELMISC-100"
    assert fetcher.is_jira_filled_for_container("unknown") == ""


def test_check_if_jira_is_filled_returns_false_when_details_missing(fetcher):
    fetcher.jira_details = None

    assert fetcher.check_if_jira_is_filled() is False
    assert fetcher.jira_deprecated_opened_issues == []


def test_check_if_jira_is_filled_collects_allowed_status_issues(fetcher):
    allowed_status = ALLOWED_STATUSES[0]
    fetcher.jira_details = [
        {"outwardIssue": {"key": "SKIP-1"}},
        {
            "inwardIssue": {
                "key": "RHELMISC-200",
                "fields": {
                    "summary": "EOL python39 RHEL9",
                    "status": {"name": "Closed"},
                },
            }
        },
        {
            "inwardIssue": {
                "key": "RHELMISC-201",
                "fields": {
                    "summary": "EOL nodejs RHEL9",
                    "status": {"name": allowed_status},
                },
            }
        },
    ]

    assert fetcher.check_if_jira_is_filled() is True
    assert fetcher.jira_deprecated_opened_issues == [
        {
            "issue_status": allowed_status,
            "summary": "EOL nodejs RHEL9",
            "jira_issue_id": "RHELMISC-201",
        }
    ]


def test_check_if_jira_is_filled_skips_links_without_inward_issue(fetcher):
    fetcher.jira_details = [{"type": {"name": "Relates"}}]

    assert fetcher.check_if_jira_is_filled() is True
    assert fetcher.jira_deprecated_opened_issues == []
