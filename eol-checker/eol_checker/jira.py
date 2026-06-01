import os
import logging

from typing import List, Dict

from requests.exceptions import HTTPError
from atlassian import Jira

from eol_checker.constants import JIRA_URL, JIRA_DEPRECATION_TICKET, ALLOWED_STATUSES

logger = logging.getLogger(__name__)


class JiraFetcher:
    def __init__(self):
        self._jira_api = None
        self.jira_deprecation_ticket: str = os.getenv(
            "JIRA_DEPRECATION_TICKET", JIRA_DEPRECATION_TICKET
        )
        self.jira_url = os.getenv("JIRA_URL", JIRA_URL)
        self.jira_details: dict = None
        self.jira_deprecated_opened_issues: List[Dict[str, str]] = []

    @property
    def jira(self) -> Jira:
        if self._jira_api is None:
            jira_token = os.getenv("JIRA_TOKEN", "")
            jira_username = os.getenv("JIRA_USERNAME", "")
            logger.debug("JIRA token: '%s'", jira_token)
            logger.debug("JIRA username: '%s'", jira_username)
            if not all((jira_token, jira_username)):
                logger.error("JIRA_TOKEN and/or JIRA_USERNAME are not set")
                return None
            self._jira_api = Jira(
                url=self.jira_url,
                username=jira_username,
                password=jira_token,
                cloud=True,
            )
            logger.debug("JIRA API initialized with URL: '%s' '%s'", self.jira_url, self._jira_api)
        return self._jira_api

    def get_jira_deprecation_details(self):
        """
        Get the JIRA details.
        Returns:
            The JIRA details.
        """
        logger.debug("JIRA deprecation ticket details: '%s'", self.jira_deprecation_ticket)
        try:
            issue = self.jira.issue(self.jira_deprecation_ticket)
            if "fields" in issue and "issuelinks" in issue["fields"]:
                self.jira_details = issue["fields"]["issuelinks"]
        except HTTPError as e:
            logger.error("Error occurred while fetching JIRA issue: %s", e)

    def is_jira_filled_for_container(self, stream_name: str) -> str:
        jira_id = ""
        for issue in self.jira_deprecated_opened_issues:
            logger.info("Check is stream '%s' in issue '%s'", stream_name, issue)
            if "summary" in issue and stream_name in issue["summary"]:
                jira_id = issue["jira_issue_id"]
                break
        return jira_id

    def check_if_jira_is_filled(self) -> bool:
        """
        Check if the JIRA ticket is filled.
        Returns:
            True if the JIRA is filled, False otherwise.
        """
        if self.jira_details is None:
            return False
        for link in self.jira_details:
            if "inwardIssue" not in link:
                logger.info(
                    "No cloned issue found for main deprecation ticket: %s",
                    self.jira_deprecation_ticket,
                )
                continue
            inward_issue = link["inwardIssue"]
            if (
                "status" not in inward_issue["fields"]
                or inward_issue["fields"]["status"]["name"] not in ALLOWED_STATUSES
            ):
                continue
            logger.debug("Cloned issue found: '%s'", inward_issue)
            issue_status = inward_issue["fields"]["status"]["name"]
            summary = inward_issue["fields"]["summary"]
            logger.info(
                "Cloned issue found with\nSummary:%s\nStatus:%s\nJira issue id: %s",
                summary,
                issue_status,
                inward_issue["key"],
            )

            self.jira_deprecated_opened_issues.append(
                {
                    "issue_status": issue_status,
                    "summary": summary,
                    "jira_issue_id": inward_issue["key"],
                }
            )
        logger.info("Deprecated issues: '%s'", self.jira_deprecated_opened_issues)
        return True
