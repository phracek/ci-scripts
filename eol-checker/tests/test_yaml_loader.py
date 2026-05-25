import requests
import yaml
from flexmock import flexmock

from eol_checker import yaml_loader as yaml_loader_module
from eol_checker.yaml_loader import YamlLoader


def test_get_yaml_url_builds_gitlab_raw_url(monkeypatch):
    monkeypatch.setenv("LIFECYCLE_DEFS_URL", "https://gitlab.example.com/group/repo")
    url = YamlLoader.get_yaml_url("RHEL9", "nodejs")
    assert (
        url
        == "https://gitlab.example.com/group/repo/-/raw/main/RHEL9/nodejs.yaml?ref_type=heads"
    )

def test_download_yaml_returns_parsed_content():
    mock_response = flexmock(
        status_code=200, content=b"lifecycles:\n  - name: nodejs\n"
    )
    mock_response.should_receive("raise_for_status").once()
    flexmock(yaml_loader_module.requests).should_receive("get").with_args(
        "https://example.com/lifecycle.yaml", timeout=30, verify=False
    ).once().and_return(mock_response)

    result = YamlLoader.download_yaml("https://example.com/lifecycle.yaml")

    assert result == {"lifecycles": [{"name": "nodejs"}]}


def test_download_yaml_returns_none_on_request_error():
    flexmock(yaml_loader_module.requests).should_receive("get").and_raise(
        requests.exceptions.RequestException("connection failed")
    )

    assert YamlLoader.download_yaml("https://example.com/lifecycle.yaml") is None


def test_download_yaml_returns_none_on_invalid_yaml():
    mock_response = flexmock(status_code=200, content=b"[\n  unclosed")
    mock_response.should_receive("raise_for_status")
    flexmock(yaml_loader_module.requests).should_receive("get").and_return(
        mock_response
    )
    flexmock(yaml_loader_module.yaml).should_receive("safe_load").and_raise(
        yaml.YAMLError("parse error")
    )

    assert YamlLoader.download_yaml("https://example.com/lifecycle.yaml") is None


def test_download_yaml_returns_none_on_http_error():
    mock_response = flexmock()
    mock_response.should_receive("raise_for_status").and_raise(
        requests.exceptions.HTTPError("404")
    )
    flexmock(yaml_loader_module.requests).should_receive("get").and_return(
        mock_response
    )

    assert YamlLoader.download_yaml("https://example.com/missing.yaml") is None
