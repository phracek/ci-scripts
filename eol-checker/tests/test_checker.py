from datetime import date

import pytest
from flexmock import flexmock

from eol_checker import checker as checker_module
from eol_checker.checker import ContainerEolChecker
from eol_checker.constants import (
    DEFAULT_YAML_URL,
    JIRA_DEPRECATION_TICKET,
    JIRA_URL,
    OS_NAMES,
)


@pytest.fixture
def checker():
    return ContainerEolChecker(today=date(2025, 5, 15))


@pytest.fixture
def checker_with_os_context(checker):
    checker.os_name = "RHEL9"
    checker.container_to_analyze = "nodejs"
    checker.eol_images["RHEL9"] = {}
    checker.approaching_eol_images["RHEL9"] = {}
    return checker


def test_init_uses_defaults():
    instance = ContainerEolChecker()

    assert instance.url == DEFAULT_YAML_URL
    assert instance.today == date.today()
    assert instance.eol_images == {}
    assert instance.approaching_eol_images == {}


def test_init_uses_provided_today_and_url():
    custom_today = date(2024, 1, 1)
    instance = ContainerEolChecker(url="http://custom/", today=custom_today)

    assert instance.url == "http://custom/"
    assert instance.today == custom_today


def test_check_enddate_skips_when_enddate_missing(checker_with_os_context):
    checker_with_os_context.check_enddate({"application_stream_name": "nodejs-18"})

    assert checker_with_os_context.eol_images["RHEL9"] == {}
    assert checker_with_os_context.approaching_eol_images["RHEL9"] == {}


def test_check_enddate_records_eol_image(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-18", "enddate": "20250530"}
    )

    assert checker_with_os_context.eol_images["RHEL9"]["nodejs"] == {
        "name": "nodejs-18"
    }
    assert "nodejs" not in checker_with_os_context.approaching_eol_images["RHEL9"]


def test_check_enddate_records_approaching_eol_image(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-20", "enddate": "20250615"}
    )

    assert checker_with_os_context.approaching_eol_images["RHEL9"]["nodejs"] == {
        "name": "nodejs-20"
    }
    assert "nodejs" not in checker_with_os_context.eol_images["RHEL9"]


def test_check_enddate_ignores_distant_enddate(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-22", "enddate": "20251231"}
    )

    assert checker_with_os_context.eol_images["RHEL9"] == {}
    assert checker_with_os_context.approaching_eol_images["RHEL9"] == {}


def test_analyze_lifecycle_yaml_processes_all_lifecycles(checker_with_os_context):
    flexmock(checker_with_os_context).should_receive("check_enddate").twice()

    checker_with_os_context.analyze_lifecycle_yaml(
        {
            "lifecycles": [
                {"application_stream_name": "nodejs-18", "enddate": "20250501"},
                {"application_stream_name": "nodejs-20", "enddate": "20250601"},
            ]
        }
    )


def test_analyze_lifecycle_yaml_integrates_check_enddate(checker_with_os_context):
    checker_with_os_context.analyze_lifecycle_yaml(
        {
            "lifecycles": [
                {"application_stream_name": "nodejs-18", "enddate": "20250501"}
            ]
        }
    )

    assert checker_with_os_context.eol_images["RHEL9"]["nodejs"] == {
        "name": "nodejs-18"
    }


def test_summary_for_eol_images_with_existing_jira_ticket(checker):
    checker.eol_images["RHEL9"] = {"nodejs": {"name": "nodejs-18"}}
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="nodejs-18").and_return("RHELMISC-100")

    report = checker.summary_for_eol_images("RHEL9")

    assert report.startswith("Summary report that reached EOL dates:\n")
    assert "nodejs-18 for RHEL9" in report
    assert "Jira ticket is already filed" in report
    assert f"{JIRA_URL}/browse/RHELMISC-100" in report


def test_summary_for_eol_images_without_jira_ticket(checker):
    checker.eol_images["RHEL9"] = {"nodejs": {"name": "nodejs-18"}}
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="nodejs-18").and_return("")

    report = checker.summary_for_eol_images("RHEL9")

    assert "Jira ticket is not filled" in report
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in report


def test_summary_for_approaching_eol_images_returns_empty_when_none(checker):
    checker.approaching_eol_images["RHEL9"] = {}

    assert checker.summary_for_approaching_eol_images("RHEL9") == ""


def test_summary_for_approaching_eol_images_with_existing_jira_ticket(checker):
    checker.approaching_eol_images["RHEL9"] = {"nodejs": {"name": "nodejs-20"}}
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="nodejs-20").and_return("RHELMISC-200")

    report = checker.summary_for_approaching_eol_images("RHEL9")

    assert report.startswith("Summary report that approaching EOL dates:\n")
    assert "nodejs-20 for RHEL9" in report
    assert "Jira ticket should be already filed" in report
    assert f"{JIRA_URL}/browse/RHELMISC-200" in report


def test_summary_for_approaching_eol_images_without_jira_ticket(checker):
    checker.approaching_eol_images["RHEL9"] = {"nodejs": {"name": "nodejs-20"}}
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="nodejs-20").and_return("")

    report = checker.summary_for_approaching_eol_images("RHEL9")

    assert "Jira ticket is not filled" in report
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in report


def test_summary_report_includes_eol_and_approaching_sections(checker):
    for os_name in OS_NAMES:
        checker.eol_images[os_name] = {}
        checker.approaching_eol_images[os_name] = {}
    checker.eol_images["RHEL9"] = {"nodejs": {"name": "nodejs-18"}}
    checker.approaching_eol_images["RHEL10"] = {"httpd": {"name": "httpd-26"}}
    checker.jira_fetcher.jira = flexmock()  # Ensure jira connection is non-None
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="nodejs-18").and_return("RHELMISC-100")
    flexmock(checker.jira_fetcher).should_receive(
        "is_jira_filled_for_container"
    ).with_args(stream_name="httpd-26").and_return("")

    report = checker.summary_report()

    assert "Summary report that reached EOL dates:" in report
    assert "nodejs-18 for RHEL9" in report
    assert "Summary report that approaching EOL dates:" in report
    assert "httpd-26 for RHEL10" in report


def test_summary_report_returns_newline_when_no_images(checker):
    for os_name in OS_NAMES:
        checker.eol_images[os_name] = {}
        checker.approaching_eol_images[os_name] = {}

    assert checker.summary_report() == "\n\n"


def test_analyze_containers_skips_when_yaml_download_fails(checker):
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return(
        "http://test/yaml"
    )
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(None)
    flexmock(checker).should_receive("analyze_lifecycle_yaml").never()

    checker.analyze_containers()

    for os_name in OS_NAMES:
        assert checker.eol_images[os_name] == {}
        assert checker.approaching_eol_images[os_name] == {}


def test_analyze_containers_analyzes_downloaded_yaml(checker):
    lifecycle_data = {
        "lifecycles": [{"application_stream_name": "nodejs-18", "enddate": "20250501"}]
    }
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return(
        "http://test/yaml"
    )
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(
        lifecycle_data
    )
    flexmock(checker).should_receive("analyze_lifecycle_yaml").with_args(
        lifecycle_data
    ).at_least().once()

    checker.analyze_containers()


def test_analyze_containers_populates_eol_from_yaml(checker):
    lifecycle_data = {
        "lifecycles": [{"application_stream_name": "nodejs-18", "enddate": "20250501"}]
    }
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return(
        "http://test/yaml"
    )
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(
        lifecycle_data
    )

    checker.analyze_containers()

    for os_name in OS_NAMES:
        assert checker.eol_images[os_name]["nodejs"] == {"name": "nodejs-18"}


def test_run_fetches_jira_and_analyzes_containers(checker):
    flexmock(checker.jira_fetcher).should_receive("get_jira_deprecation_details").once()
    flexmock(checker.jira_fetcher).should_receive("check_if_jira_is_filled").once()
    flexmock(checker).should_receive("analyze_containers").once()
    flexmock(checker).should_receive("summary_report").and_return("\nreport\n")

    checker.run()
