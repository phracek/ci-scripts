from datetime import date

import pytest
import smtplib
from flexmock import flexmock

from eol_checker import checker as checker_module
from eol_checker.checker import ContainerEolChecker
from eol_checker.constants import JIRA_DEPRECATION_TICKET, JIRA_URL, OS_NAMES


@pytest.fixture
def checker(monkeypatch):
    monkeypatch.setenv("DEFAULT_EMAILS", "default@redhat.com")
    instance = ContainerEolChecker(send_email=False)
    instance.today = date(2025, 5, 15)
    return instance


@pytest.fixture
def checker_with_os_context(checker):
    checker.os_name = "RHEL9"
    checker.container_to_analyze = "nodejs"
    checker.eol_images["RHEL9"] = {}
    checker.approaching_eol_images["RHEL9"] = {}
    checker.already_eol_images["RHEL9"] = {}
    return checker


def _container_struct(name, enddate):
    return {"name": name, "enddate": enddate}


def test_init_defaults(monkeypatch):
    monkeypatch.setenv("DEFAULT_EMAILS", "default@redhat.com")
    monkeypatch.delenv("DEBUG", raising=False)
    monkeypatch.delenv("SEND_EMAIL", raising=False)
    instance = ContainerEolChecker()

    assert instance.today == date.today()
    assert instance.send_email is False
    assert instance.end_line == "\n"
    assert instance.bold_line == ""
    assert instance.default_mails == ["default@redhat.com"]
    assert instance.eol_images == {}
    assert instance.body == ""


def test_init_send_email_formatting(monkeypatch):
    monkeypatch.setenv("DEFAULT_EMAILS", "default@redhat.com")
    instance = ContainerEolChecker(send_email=True)

    assert instance.end_line == "<br>"
    assert instance.bold_line == "<b>"
    assert instance.bold_line_end == "</b>"


def test_init_loads_default_emails_from_environment(monkeypatch):
    monkeypatch.setenv("DEFAULT_EMAILS", "one@redhat.com,two@redhat.com")

    instance = ContainerEolChecker()

    assert instance.default_mails == ["one@redhat.com", "two@redhat.com"]


def test_check_enddate_skips_when_required_fields_missing(checker_with_os_context):
    checker_with_os_context.check_enddate({"application_stream_name": "nodejs-18"})

    assert checker_with_os_context.eol_images["RHEL9"] == {}
    assert checker_with_os_context.approaching_eol_images["RHEL9"] == {}
    assert checker_with_os_context.already_eol_images["RHEL9"] == {}


def test_check_enddate_skips_invalid_enddate(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-18", "enddate": "not-a-date"}
    )

    assert checker_with_os_context.eol_images["RHEL9"] == {}


def test_check_enddate_records_eol_image(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-18", "enddate": "20250530"}
    )

    assert checker_with_os_context.eol_images["RHEL9"]["nodejs"] == _container_struct(
        "nodejs-18", "20250530"
    )


def test_check_enddate_records_approaching_eol_image(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-20", "enddate": "20250615"}
    )

    assert checker_with_os_context.approaching_eol_images["RHEL9"]["nodejs"] == (
        _container_struct("nodejs-20", "20250615")
    )


def test_check_enddate_records_already_eol_image(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-16", "enddate": "20250415"}
    )

    assert checker_with_os_context.already_eol_images["RHEL9"]["nodejs"] == (
        _container_struct("nodejs-16", "20250415")
    )


def test_check_enddate_ignores_distant_enddate(checker_with_os_context):
    checker_with_os_context.check_enddate(
        {"application_stream_name": "nodejs-22", "enddate": "20251231"}
    )

    assert checker_with_os_context.eol_images["RHEL9"] == {}
    assert checker_with_os_context.approaching_eol_images["RHEL9"] == {}
    assert checker_with_os_context.already_eol_images["RHEL9"] == {}


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


def test_get_jira_msg_without_filed_ticket(checker):
    message = checker._get_jira_msg("reached EOL", "20250501")

    assert "reached EOL in 20250501" in message
    assert "Jira ticket is not filled" in message
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in message


def test_get_jira_msg_with_filed_ticket(checker):
    message = checker._get_jira_msg("approaching EOL", "20250601", jira_id="RHELMISC-999")

    assert "approaching EOL in 20250601" in message
    assert "Jira ticket is already filed" in message
    assert f"{JIRA_URL}/browse/RHELMISC-999" in message


def test_get_jira_msg_html_links_when_sending_email(checker):
    checker.send_email = True
    checker.bold_line = "<b>"
    checker.bold_line_end = "</b>"

    message = checker._get_jira_msg("reached EOL", "20250501")

    assert "<a href='" in message
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in message


def test_summary_for_images_returns_empty_when_no_containers(checker):
    checker.eol_images["RHEL9"] = {}

    assert checker.summary_for_images(checker.eol_images, "RHEL9") == ""


def test_summary_for_images_when_jira_unavailable(checker):
    checker.eol_images["RHEL9"] = {"nodejs": _container_struct("nodejs-18", "20250501")}
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(None)

    report = checker.summary_for_images(checker.eol_images, "RHEL9")

    assert "Summary report for RHEL9:" in report
    assert "nodejs-18 for RHEL9" in report
    assert "Jira ticket is not filled" in report
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in report


def test_summary_for_images_without_jira_ticket(checker):
    checker.eol_images["RHEL9"] = {"nodejs": _container_struct("nodejs-18", "20250501")}
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(flexmock())
    flexmock(checker.jira_fetcher).should_receive("is_jira_filed_for_container").with_args(
        stream_name="nodejs-18"
    ).and_return("")

    report = checker.summary_for_images(checker.eol_images, "RHEL9")

    assert "nodejs-18 for RHEL9" in report
    assert "Jira ticket is not filled" in report
    assert f"{JIRA_URL}/browse/{JIRA_DEPRECATION_TICKET}" in report


def test_summary_for_images_with_jira_ticket_filed(checker):
    checker.eol_images["RHEL9"] = {"nodejs": _container_struct("nodejs-18", "20250501")}
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(flexmock())
    flexmock(checker.jira_fetcher).should_receive("is_jira_filed_for_container").with_args(
        stream_name="nodejs-18"
    ).and_return("RHELMISC-500")

    report = checker.summary_for_images(checker.eol_images, "RHEL9")

    assert "nodejs-18 for RHEL9" in report
    assert "Jira ticket is already filed" in report
    assert f"{JIRA_URL}/browse/RHELMISC-500" in report


def test_summary_for_images_adds_sme_mails_when_sending_email(checker):
    checker.send_email = True
    checker.end_line = "<br>"
    checker.bold_line = "<b>"
    checker.bold_line_end = "</b>"
    checker.eol_sme_mails = {"nodejs": ["sme@redhat.com", ""]}
    checker.default_mails = ["default@redhat.com"]
    checker.eol_images["RHEL9"] = {"nodejs": _container_struct("nodejs-18", "20250501")}
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(None)

    checker.summary_for_images(checker.eol_images, "RHEL9")

    assert "sme@redhat.com" in checker.default_mails
    assert checker.default_mails.count("default@redhat.com") == 1


def test_summary_report_includes_all_eol_categories(checker):
    for os_name in OS_NAMES:
        checker.eol_images[os_name] = {}
        checker.approaching_eol_images[os_name] = {}
        checker.already_eol_images[os_name] = {}
    checker.already_eol_images["RHEL8"] = {"nodejs": _container_struct("nodejs-16", "20250401")}
    checker.eol_images["RHEL9"] = {"nodejs": _container_struct("nodejs-18", "20250501")}
    checker.approaching_eol_images["RHEL10"] = {"httpd": _container_struct("httpd-26", "20250601")}
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(None)

    report = checker.summary_report()

    assert "Summary report for RHEL8:" in report
    assert "nodejs-16 for RHEL8" in report
    assert "Summary report for RHEL9:" in report
    assert "nodejs-18 for RHEL9" in report
    assert "Summary report for RHEL10:" in report
    assert "httpd-26 for RHEL10" in report


def test_summary_report_returns_newlines_when_no_images(checker):
    for os_name in OS_NAMES:
        checker.eol_images[os_name] = {}
        checker.approaching_eol_images[os_name] = {}
        checker.already_eol_images[os_name] = {}

    assert (
        checker.summary_report()
        == "\nThe EOL checker is not able to connect to Jira. Update the Jira credentials in the environment variables.\n"
    )


def test_analyze_containers_skips_when_yaml_url_missing(checker):
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return("")
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").never()
    flexmock(checker).should_receive("analyze_lifecycle_yaml").never()

    checker.analyze_containers()

    for os_name in OS_NAMES:
        assert checker.eol_images[os_name] == {}
        assert checker.approaching_eol_images[os_name] == {}
        assert checker.already_eol_images[os_name] == {}


def test_analyze_containers_skips_when_yaml_download_fails(checker):
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return(
        "http://test/yaml"
    )
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(None)
    flexmock(checker).should_receive("analyze_lifecycle_yaml").never()

    checker.analyze_containers()


def test_analyze_containers_analyzes_downloaded_yaml(checker):
    lifecycle_data = {
        "lifecycles": [{"application_stream_name": "nodejs-18", "enddate": "20250501"}]
    }
    flexmock(checker_module.YamlLoader).should_receive("get_yaml_url").and_return(
        "http://test/yaml"
    )
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(lifecycle_data)
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
    flexmock(checker_module.YamlLoader).should_receive("download_yaml").and_return(lifecycle_data)

    checker.analyze_containers()

    for os_name in OS_NAMES:
        assert checker.eol_images[os_name]["nodejs"] == _container_struct("nodejs-18", "20250501")


def test_send_emails_sends_html_message(checker, monkeypatch):
    monkeypatch.setenv("SMTP_SERVER", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    checker.send_email = True
    checker.default_mails = ["recipient@redhat.com"]
    checker.body = "<b>report</b>"
    mock_smtp = flexmock()
    mock_smtp.should_receive("set_debuglevel").with_args(5).once()
    mock_smtp.should_receive("sendmail").once()
    mock_smtp.should_receive("close").once()
    flexmock(checker_module).should_receive("SMTP").with_args("smtp.test", 2525).and_return(
        mock_smtp
    )

    checker.send_emails()

    assert checker.smtp_server == "smtp.test"
    assert checker.smtp_port == 2525
    assert checker.mime_msg["Subject"] == "Container EOL Checker Report"
    assert "recipient@redhat.com" in checker.mime_msg["To"]


def test_send_emails_logs_smtp_exception(checker, caplog, monkeypatch):
    monkeypatch.setenv("SMTP_SERVER", "smtp.test")
    monkeypatch.setenv("SMTP_PORT", "2525")
    checker.send_email = True
    checker.default_mails = ["recipient@redhat.com"]
    checker.body = "report"
    mock_smtp = flexmock()
    mock_smtp.should_receive("set_debuglevel").and_return(None)
    mock_smtp.should_receive("sendmail").and_raise(smtplib.SMTPException("smtp failure"))
    mock_smtp.should_receive("close").once()
    flexmock(checker_module).should_receive("SMTP").and_return(mock_smtp)

    with caplog.at_level("ERROR"):
        checker.send_emails()

    assert "Error sending email(SMTPException)" in caplog.text


def test_run_skips_jira_when_connection_unavailable(checker):
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(None)
    flexmock(checker.jira_fetcher).should_receive("get_jira_deprecation_details").never()
    flexmock(checker).should_receive("analyze_containers").once()
    flexmock(checker).should_receive("summary_report").and_return("\nreport\n")
    flexmock(checker).should_receive("send_emails").never()

    assert checker.run() == 0
    assert checker.body == "\nreport\n"


def test_run_fetches_jira_and_analyzes_containers(checker):
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(flexmock())
    flexmock(checker.jira_fetcher).should_receive("get_jira_deprecation_details").once()
    flexmock(checker.jira_fetcher).should_receive("check_if_jira_is_filed").once()
    flexmock(checker).should_receive("analyze_containers").once()
    flexmock(checker).should_receive("summary_report").and_return("\nreport\n")
    flexmock(checker).should_receive("send_emails").never()

    assert checker.run() == 0


def test_run_sends_email_when_enabled(checker):
    checker.send_email = True
    flexmock(checker.jira_fetcher).should_receive("jira").and_return(None)
    flexmock(checker).should_receive("analyze_containers").once()
    flexmock(checker).should_receive("summary_report").and_return("\nreport\n")
    flexmock(checker).should_receive("send_emails").once()

    assert checker.run() == 0
