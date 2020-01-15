#!/usr/bin/python
# -*- coding: utf-8 -*-
#
import smtplib
import sys

from pathlib import Path
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

COMMASPACE = ", "


class SendResults:

    results_dir: Path = None
    sender: str = ""
    recipients: List[str] = []
    msg: MIMEMultipart = None
    # Body message for an email
    html = """
        <html>
        <head></head>
            <body>
            <p>
                Nightly build testing of RHSCL containers on CentOS {results}
                {cont}
            </p>
            </body>
        </html>
    """
    title: str = "RHSCL: CentOS containers nightly build testing."

    def __init__(self):
        """
        Parse position arguments
        1st argument: directory
        2nd argument: sender
        3rd and rest arguments: recipients
        """
        self.get_cli_args()
        self.msg = MIMEMultipart()
        self.msg["From"] = self.sender
        self.msg["To"] = COMMASPACE.join(self.recipients)
        self.msg.preamble = self.title

    def get_cli_args(self):
        """
        Parse CLI arguments
        """
        # Directory, where are stored logs
        if len(sys.argv) < 4:
            print(
                "Script `send_results.py` expects at least 3 arguments."
                "./send_results.py <directory> <sender> <recipient_1> <recipient_2> ..."
            )
            sys.exit(1)
        self.results_dir = Path(sys.argv[1])
        self.sender = sys.argv[2]
        self.recipients = sys.argv[3:]
        if not self.results_dir.exists() and not self.results_dir.is_dir():
            print("The directory specified as the first argument does not exist.")
            sys.exit(1)

    def iterate_over_dir(self) -> List:
        failed_containers: List = []
        for filename in self.results_dir.iterdir():
            if not filename.is_file() and not str(filename).endswith(".log"):
                continue
            # Open log file and attach it into message
            print(f"Failed container {str(filename)}.")
            with filename.open() as fp:
                file_attachment = MIMEText(fp.read(), "plain")
            file_attachment.add_header(
                "Content-Disposition", "attachment", filename=filename.name
            )
            self.msg.attach(file_attachment)
            # Delete log file and append into failed_containers array
            failed_containers.append(filename.stem)
            filename.unlink()
        return failed_containers

    def send_results(self):
        """
        Sends an email based on the logs from the given directory
        """
        failed_containers: List = self.iterate_over_dir()
        if failed_containers:
            short_result = "failed."
            self.msg["Subject"] = self.title + short_result
            html = self.html.format(
                results=short_result,
                cont="<br><br>Failed containers: <br>" + "<br>".join(failed_containers),
            )
        else:
            short_result = "was successful."
            self.msg["Subject"] = self.title + short_result
            html = self.html.format(results=short_result, cont="")

        self.msg.attach(MIMEText(html, "html"))
        s = smtplib.SMTP("localhost")
        s.sendmail(self.sender, self.recipients, self.msg.as_string())
        print("Email sent.")
        s.quit()


if __name__ == "__main__":
    sr = SendResults()
    sr.send_results()
