# MIT License
#
# Copyright (c) 2024 Red Hat, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
import os

from typing import Any, Iterable, Dict
from datetime import date

from eol_checker.constants import JIRA_URL

logger = logging.getLogger(__name__)


def is_eol_version(enddate: date, today: date) -> int:
    """
    Check if the version is EOL.
    Args:
        enddate: The enddate.
    Returns:
        1 if the version is EOL, 2 if the version is approaching EOL, 0 if the version is not approaching EOL.
    """
    if enddate.year == today.year and enddate.month == today.month:
        return 1
    if enddate.year == today.year and enddate.month == today.month + 1:
        return 2
    if enddate.year == today.year and enddate.month == today.month - 1:
        return 3
    return 0


def get_lifecycles(data: Any) -> Iterable[Dict[str, Any]]:
    """
    Get the lifecycles from the lifecycle YAML file.
    Args:
        data: The lifecycle YAML file content.
    Returns:
        The lifecycles.
    """
    if isinstance(data, dict) and "lifecycles" in data:
        return data["lifecycles"]
    return []


def get_jira_ticket_url(jira_issue_id: str) -> str:
    """
    Get the JIRA ticket URL.
    Args:
        jira_issue_id: The JIRA issue ID.
    Returns:
        The JIRA ticket URL.
    """
    return f"{JIRA_URL}/browse/{jira_issue_id}"


def get_env_variable(var_name: str, default_value: str = "") -> str:
    """
    Get environment variable value or return default value if not set.
    :param var_name: Name of the environment variable
    :param default_value: Default value to return if environment variable is not set
    :return: Value of the environment variable or default value
    """
    if var_name in os.environ:
        value = os.getenv(var_name, default_value)
        print(f"Environment variable '{var_name}': '{value}'")
        return value
    return default_value


def load_mails_from_environment():
    """
    Load email addresses from environment variables.
    """
    sclorg_mails = {}
    sclorg_mails["mariadb"] = get_env_variable("DB_MAILS").split(",")
    sclorg_mails["mysql"] = get_env_variable("DB_MAILS").split(",")
    sclorg_mails["postgresql"] = get_env_variable("DB_MAILS").split(",")
    sclorg_mails["ruby"] = get_env_variable("RUBY_MAILS").split(",")
    python_mails = get_env_variable("PYTHON_MAILS").split(",")
    sclorg_mails["python"] = python_mails
    sclorg_mails["python36"] = python_mails
    sclorg_mails["python38"] = python_mails
    sclorg_mails["python39"] = python_mails
    sclorg_mails["python311"] = python_mails
    sclorg_mails["python312"] = python_mails
    sclorg_mails["nodejs"] = get_env_variable("NODEJS_MAILS").split(",")
    sclorg_mails["perl"] = get_env_variable("PERL_MAILS").split(",")
    sclorg_mails["php"] = get_env_variable("PHP_MAILS").split(",")
    sclorg_mails["redis"] = get_env_variable("REDIS_MAILS").split(",")
    sclorg_mails["varnish"] = get_env_variable("VARNISH_MAILS").split(",")
    sclorg_mails["valkey"] = get_env_variable("VALKEY_MAILS").split(",")
    sclorg_mails["httpd"] = get_env_variable("HTTPD_MAILS").split(",")
    sclorg_mails["nginx"] = get_env_variable("NGINX_MAILS").split(",")
    return sclorg_mails
