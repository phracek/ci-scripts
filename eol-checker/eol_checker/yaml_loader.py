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
import requests
import yaml
import os

logger = logging.getLogger(__name__)


class YamlLoader:
    @staticmethod
    def get_yaml_url(os_name: str, container_to_analyze: str) -> str:
        """
        Get the URL for the lifecycle YAML file.
        Args:
            os_name: The name of the OS.
            container_to_analyze: The name of the container to analyze.
        Returns:
            The URL for the lifecycle YAML file.
        """
        url = os.getenv("LIFECYCLE_DEFS_URL", "")
        if url == "":
            logger.error("LIFECYCLE_DEFS_URL is not set")
            return ""
        return f"{url}/-/raw/main/{os_name}/{container_to_analyze}.yaml?ref_type=heads"

    @staticmethod
    def download_yaml(url: str) -> dict:
        """
        Download the lifecycle YAML file.
        Args:
            url: The URL of the lifecycle YAML file.
        Returns:
            The lifecycle YAML file content.
        """
        try:
            response = requests.get(url, timeout=30, verify=False)
            response.raise_for_status()
            if response.status_code != 200:
                logger.error("Failed to download lifecycle YAML file from %s", url)
                return None
        except requests.exceptions.RequestException as e:
            logger.error(
                "RequestException: Failed to download lifecycle YAML file from %s: %s",
                url,
                e,
            )
            return None

        try:
            return yaml.safe_load(response.content)
        except yaml.YAMLError as e:
            logger.error("Failed to parse lifecycle YAML file from %s: %s", url, e)
            return None
