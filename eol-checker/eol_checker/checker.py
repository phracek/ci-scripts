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
import os
import urllib3
import smtplib

from smtplib import SMTP
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, datetime
from typing import Any, Dict, List

from eol_checker.jira import JiraFetcher
from eol_checker.custom_logger import setup_logger
from eol_checker.yaml_loader import YamlLoader
from eol_checker.utils import (
    get_jira_ticket_url,
    is_eol_version,
    get_lifecycles,
    load_mails_from_environment,
    get_env_variable,
)
from eol_checker.constants import OS_NAMES, CONTAINER_NAMES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ContainerEolChecker(object):
    """
    Checker for container image EOL dates from lifecycle YAML.
    """

    def __init__(self, debug: bool = False, send_email: bool = False):
        self.today = date.today()
        self.lifecycle_data: Any = None
        self.eol_images: dict = {}
        self.already_eol_images: dict = {}
        self.approaching_eol_images: dict = {}
        self.os_name: str = ""
        self.default_mails: List[str] = os.getenv("DEFAULT_EMAILS", "").split(",")
        self.container_to_analyze: str = ""
        self.jira_fetcher = JiraFetcher()
        self.eol_sme_mails = load_mails_from_environment()
        # Used for OpenShift CronJob
        env_debug = os.getenv("DEBUG")
        debug_enabled = (
            debug if env_debug is None else env_debug.strip().lower() in {"1", "true", "yes", "on"}
        )
        self._setup_logger(debug=debug_enabled)

        env_send_email = os.getenv("SEND_EMAIL")
        self.send_email = (
            send_email
            if env_send_email is None
            else env_send_email.strip().lower() in {"1", "true", "yes", "on"}
        )
        self.smtp_port = 25
        self.smtp_server = "smtp.redhat.com"
        self.end_line = "<br>" if self.send_email else "\n"
        self.bold_line = "<b>" if self.send_email else ""
        self.bold_line_end = "</b>" if self.send_email else ""
        self.mime_msg = MIMEMultipart()
        self.body = ""

    def _setup_logger(self, debug: bool = False):
        """
        Setup the logger.
        Args:
            debug: The debug flag.
        """
        if debug:
            setup_logger(level=logging.DEBUG)
        else:
            setup_logger(level=logging.INFO)

    def check_enddate(self, lifecycle: Dict[str, Any]) -> None:
        """
        Check the enddate of the lifecycle.
        Args:
            lifecycle: The lifecycle.
        """
        if "enddate" not in lifecycle or "application_stream_name" not in lifecycle:
            logger.warning("Skipping lifecycle missing required fields: %s", lifecycle)
            return

        application_stream_name = lifecycle["application_stream_name"]
        str_enddate = str(lifecycle["enddate"])
        try:
            enddate = datetime.strptime(str_enddate, "%Y%m%d").date()
        except (TypeError, ValueError):
            logger.warning("Skipping lifecycle with invalid enddate: %s", lifecycle)
            return

        logger.debug(
            "Enddate('%s'): '%s' and today is '%s'",
            application_stream_name,
            enddate,
            self.today,
        )
        container_struct = {"name": application_stream_name, "enddate": str_enddate}
        is_eol = is_eol_version(enddate, self.today)
        eol_msg = ""
        if is_eol == 1:
            eol_msg = f"Deprecation should be processed for image stream {application_stream_name}: enddate is {enddate}"
            self.eol_images[self.os_name][self.container_to_analyze] = container_struct
        if is_eol == 2:
            eol_msg = f"Deprecation of image stream {application_stream_name} is approaching next month should be scheduled: enddate is {enddate}"
            self.approaching_eol_images[self.os_name][self.container_to_analyze] = container_struct
        if is_eol == 3:
            eol_msg = f"Deprecation of image stream {application_stream_name} already approached one month ago should be scheduled: enddate is {enddate}"
            self.already_eol_images[self.os_name][self.container_to_analyze] = container_struct
        if is_eol != 0:
            logger.info(eol_msg)

    def analyze_lifecycle_yaml(self, data: Any) -> None:
        """
        Analyze the lifecycle YAML file.
        For each lifecycle, check the enddate and log the result.
        Args:
            data: The lifecycle YAML file content.
        """
        for lifecycle in get_lifecycles(data):
            self.check_enddate(lifecycle)

    def _get_jira_msg(self, report_type: str, enddate: str) -> str:
        """
        Generate a Jira message.
        Args:
            report_type: The report type.
            enddate: The enddate.
        Returns:
            The Jira message.
        """
        jira_msg = (
            "Connection to Jira not available"
            if self.jira_fetcher.jira is None
            else "Jira ticket is not filled. Use Jira issue template:"
        )
        return self.bold_line + f"{report_type} in {enddate}" + self.bold_line_end + f". {jira_msg}"

    def summary_for_images(self, images: dict, os_name: str, eol_type: bool = True) -> str:
        """
        Generate a summary report for the images.
        Args:
            images: The images.
            os_name: The OS name.
            eol_type: The EOL type. True for EOL, False for approaching EOL.
        Returns:
            The summary report.
        """
        if len(images[os_name]) == 0:
            return ""
        report_type = "reached EOL" if eol_type else "approaching EOL"
        report = "\n"
        report += (
            self.bold_line + f"Summary report for {os_name}:" + self.bold_line_end + self.end_line
        )
        logger.debug("EOL images: '%s'", images)
        for container_name, values in images[os_name].items():
            logger.info("Processing container: '%s' with values: '%s'", container_name, values)
            stream_name = values["name"]
            if self.send_email:
                for mail in self.eol_sme_mails[container_name]:
                    if mail and mail not in self.default_mails:
                        self.default_mails.append(mail)
            if self.jira_fetcher.jira is None:
                logger.error("Connection to Jira failed")
                jira_msg = self._get_jira_msg(report_type=report_type, enddate=values["enddate"])
                jira_id = self.jira_fetcher.jira_deprecation_ticket
                jira_url = get_jira_ticket_url(jira_issue_id=jira_id)
                url = f"<a href='{jira_url}'>{jira_url}</a>" if self.send_email else jira_url
                report += f"{stream_name} for {os_name} {jira_msg} {url}{self.end_line}"
                continue
            jira_msg = self._get_jira_msg(report_type=report_type, enddate=values["enddate"])
            jira_msg += "Jira ticket is already filed:"
            jira_id = self.jira_fetcher.is_jira_filled_for_container(stream_name=stream_name)
            if jira_id == "":
                jira_msg = self._get_jira_msg(report_type=report_type, enddate=values["enddate"])
                jira_id = self.jira_fetcher.jira_deprecation_ticket
                jira_url = get_jira_ticket_url(jira_issue_id=jira_id)
                url = f"<a href='{jira_url}'>{jira_url}</a>" if self.send_email else jira_url
                report += f"{stream_name} for {os_name} {jira_msg} {url}{self.end_line}"
            report += "\n"

        return report

    def summary_report(self) -> str:
        """
        Generate a summary report of the container EOL checker.
        Returns:
            The summary report.
        """
        report = "\n"
        if self.jira_fetcher.jira is None:
            report += "The EOL checker is not able to connect to Jira. Update the Jira credentials in the environment variables."
        for os_name in OS_NAMES:
            if len(self.already_eol_images[os_name]) != 0:
                report += self.summary_for_images(images=self.already_eol_images, os_name=os_name)
            if len(self.eol_images[os_name]) != 0:
                report += self.summary_for_images(images=self.eol_images, os_name=os_name)
            if len(self.approaching_eol_images[os_name]) != 0:
                report += self.summary_for_images(
                    images=self.approaching_eol_images, os_name=os_name, eol_type=False
                )
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
            self.already_eol_images[os_name] = {}
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
                    logger.error("Failed to download lifecycle YAML file from '%s'", yaml_url)
                    continue
                self.analyze_lifecycle_yaml(self.lifecycle_data)
            logger.info("Analyzing OS %s completed", self.os_name)

    def send_emails(self):
        """
        Send emails with the container EOL information.
        """
        logger.debug("Sending emails is enabled")
        logger.debug(", ".join(self.default_mails))
        self.smtp_server = get_env_variable("SMTP_SERVER", "smtp.redhat.com")
        self.smtp_port = int(get_env_variable("SMTP_PORT", "25"))

        send_from = "phracek@redhat.com"
        send_to = self.default_mails
        self.mime_msg["From"] = send_from
        self.mime_msg["To"] = ", ".join(send_to)
        self.mime_msg["Subject"] = "Container EOL Checker Report"
        logger.debug(
            "Sending email with subject: 'Container EOL Checker Report' to: '%s'",
            send_to,
        )
        logger.debug("Email body: '%s'", self.body)
        logger.debug("Message: '%s'", self.mime_msg)
        self.mime_msg.attach(MIMEText(self.body, "html"))
        try:
            smtp = SMTP(self.smtp_server, int(self.smtp_port))
            smtp.set_debuglevel(5)
            smtp.sendmail(send_from, send_to, self.mime_msg.as_string())
        except smtplib.SMTPRecipientsRefused as e:
            logger.error("Error sending email(SMTPRecipientsRefused): %s", e.strerror)
        except smtplib.SMTPException as e:
            logger.error("Error sending email(SMTPException): %s", e)
        finally:
            smtp.close()
        logger.debug("Sending email finished")

    def run(self):
        """
        Run the container EOL checker.
        """
        logger.info("Running container EOL checker")
        if self.jira_fetcher.jira is None:
            logger.error("Connection to Jira failed")
        else:
            self.jira_fetcher.get_jira_deprecation_details()
            self.jira_fetcher.check_if_jira_is_filled()
        self.analyze_containers()
        self.body = self.summary_report()
        logger.info(self.body)
        if self.send_email:
            self.send_emails()
        else:
            logger.info("Sending emails is disabled")
        return 0
