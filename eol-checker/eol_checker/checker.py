#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# The MIT License (MIT)
#
# Copyright (c) 2025  Authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Petr Hracek <phracek@redhat.com>

import logging
import urllib3

from datetime import date, datetime
from typing import Any, Dict

from eol_checker.jira import JiraFetcher
from eol_checker.yaml_loader import YamlLoader
from eol_checker.utils import get_jira_ticket_url, is_eol_version, get_lifecycles
from eol_checker.constants import OS_NAMES, CONTAINER_NAMES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ContainerEolChecker(object):
    """
    Checker for container image EOL dates from lifecycle YAML.
    """

    def __init__(self):
        self.today = date.today()
        self.lifecycle_data: Any = None
        self.eol_images: dict = {}
        self.approaching_eol_images: dict = {}
        self.os_name: str = ""
        self.container_to_analyze: str = ""
        self.jira_fetcher = JiraFetcher()

    def check_enddate(self, lifecycle: Dict[str, Any]) -> None:
        """
        Check the enddate of the lifecycle.
        Args:
            lifecycle: The lifecycle.
        """
        if "enddate" not in lifecycle:
            return

        application_stream_name = lifecycle["application_stream_name"]
        enddate = datetime.strptime(lifecycle["enddate"], "%Y%m%d").date()

        logger.debug(
            "Enddate('%s'): '%s' and today is '%s'",
            application_stream_name,
            enddate,
            self.today,
        )
        is_eol = is_eol_version(enddate, self.today)
        if is_eol == 1:
            logger.info(
                "Deprecation should be processed for image stream %s: enddate is '%s'",
                application_stream_name,
                enddate,
            )
            self.eol_images[self.os_name][self.container_to_analyze] = {
                "name": application_stream_name
            }
        if is_eol == 2:
            logger.info(
                "Deprecation of image stream %s is approaching next month should be scheduled: enddate is '%s'",
                application_stream_name,
                enddate,
            )
            self.approaching_eol_images[self.os_name][self.container_to_analyze] = {
                "name": application_stream_name
            }

    def analyze_lifecycle_yaml(self, data: Any) -> None:
        """
        Analyze the lifecycle YAML file.
        For each lifecycle, check the enddate and log the result.
        Args:
            data: The lifecycle YAML file content.
        """
        for lifecycle in get_lifecycles(data):
            self.check_enddate(lifecycle)

    def summary_for_eol_images(self, os_name: str) -> str:
        """
        Generate a summary report for the EOL images.
        Args:
            os_name: The OS name.
        Returns:
            The summary report.
        """
        report = "Summary report that reached EOL dates:\n"
        logger.debug("EOL images: '%s'", self.eol_images)
        for container_name, values in self.eol_images[os_name].items():
            logger.info(
                "Processing container: '%s' with values: '%s'", container_name, values
            )
            stream_name = values["name"]
            if self.jira_fetcher.jira is None:
                logger.error("Connection to Jira failed")
                jira_msg = (
                    "reached EOL. Jira ticket is not filled. Use Jira issue template:"
                )
                jira_id = self.jira_fetcher.jira_deprecation_ticket
                report += f"{stream_name} for {os_name} {jira_msg} {get_jira_ticket_url(jira_issue_id=jira_id)}\n"
                continue
            jira_msg = "reached EOL. Jira ticket is already filed:"
            jira_id = self.jira_fetcher.is_jira_filled_for_container(
                stream_name=stream_name
            )
            logger.info("Jira id for stream '%s' is '%s'", stream_name, jira_id)
            if jira_id == "":
                jira_msg = (
                    "reached EOL. Jira ticket is not filled. Use Jira issue template:"
                )
                jira_id = self.jira_fetcher.jira_deprecation_ticket
            report += f"{stream_name} for {os_name} {jira_msg} {get_jira_ticket_url(jira_issue_id=jira_id)}\n"

        return report

    def summary_for_approaching_eol_images(self, os_name: str) -> str:
        """
        Generate a summary report for the approaching EOL images.
        Args:
            os_name: The OS name.
        Returns:
            The summary report.
        """
        if len(self.approaching_eol_images[os_name]) == 0:
            return ""
        report = "Summary report that approaching EOL dates:\n"
        for container_name, values in self.approaching_eol_images[os_name].items():
            logger.info(
                "Processing container: '%s' with values: '%s'", container_name, values
            )
            stream_name = values["name"]
            jira_msg = "is approaching EOL. Jira ticket should be already filed:"
            jira_id = self.jira_fetcher.is_jira_filled_for_container(
                stream_name=stream_name
            )
            logger.info("Jira id for stream '%s' is '%s'", stream_name, jira_id)
            if jira_id == "":
                jira_msg = "is approaching EOL. Jira ticket is not filled. Use Jira issue template:"
                jira_id = self.jira_fetcher.jira_deprecation_ticket
            report += f"{stream_name} for {os_name} {jira_msg} ({get_jira_ticket_url(jira_issue_id=jira_id)})\n"

        return report

    def summary_report(self) -> str:
        """
        Generate a summary report of the container EOL checker.
        Returns:
            The summary report.
        """
        report = "\n"
        for os_name in OS_NAMES:
            if len(self.eol_images[os_name]) != 0:
                report += self.summary_for_eol_images(os_name)
            if len(self.approaching_eol_images[os_name]) != 0:
                report += self.summary_for_approaching_eol_images(os_name)
        report += "\n"
        return report

    def analyze_containers(self):
        """
        Run the container EOL checker.
        """
        for os_name in OS_NAMES:
            logger.info("Analyzing OS %s", os_name)
            self.os_name = os_name
            self.eol_images[os_name] = {}
            self.approaching_eol_images[os_name] = {}
            for container_name in CONTAINER_NAMES:
                self.container_to_analyze = container_name
                yaml_url = YamlLoader.get_yaml_url(os_name, container_name)
                if yaml_url == "":
                    logger.error(
                        "YAML URL is not set for container '%s' and OS '%s'",
                        container_name,
                        os_name,
                    )
                    continue
                self.lifecycle_data = YamlLoader.download_yaml(yaml_url)
                if self.lifecycle_data is None:
                    logger.error(
                        "Failed to download lifecycle YAML file from '%s'", yaml_url
                    )
                    continue
                self.analyze_lifecycle_yaml(self.lifecycle_data)
            logger.info("Analyzing OS %s completed", self.os_name)

    def run(self):
        """
        Run the container EOL checker.
        """
        if self.jira_fetcher.jira is None:
            logger.error("Connection to Jira failed")
        else:
            self.jira_fetcher.get_jira_deprecation_details()
            self.jira_fetcher.check_if_jira_is_filled()
        self.analyze_containers()
        logger.info(self.summary_report())
        return 0
