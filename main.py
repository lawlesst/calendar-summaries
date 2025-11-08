import smtplib
import tempfile
import webbrowser
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from pydoc import cli
from zoneinfo import ZoneInfo

import click
from gcsa.calendar import Calendar
from gcsa.google_calendar import GoogleCalendar
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings

creds = Path(__file__).parent / "creds" / "credentials.json"


def get_events(calendar_id: str, days: int):
    gc = GoogleCalendar(credentials_path=creds)
    events = gc.get_events(
        calendar_id=calendar_id,
        time_min=datetime.now(),
        time_max=datetime.now() + timedelta(days=days),
        single_events=True,
        order_by="startTime",
    )
    grouped = defaultdict(list)
    for e in events:
        day = e.start.date()
        e.start = e.start.astimezone(ZoneInfo("America/New_York"))
        e.end = e.end.astimezone(ZoneInfo("America/New_York"))
        grouped[day].append(e)
    return grouped


def render_email(events_by_day):
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"])
    )
    template = env.get_template("weekly-email.html.jinja2")
    return template.render(events_by_day=events_by_day)


def send_email(subject, html_body, to_addresses, email_from):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(to_addresses)

    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP_SSL(settings.email_host, settings.email_port) as server:
        server.login(settings.email_username, settings.email_password)
        server.send_message(msg)


@click.command()
@click.option(
    "--calendar-id",
    default=settings.default_calendar_id,
    help="Google Calendar ID to fetch events from.",
)
@click.option(
    "--days",
    default=6,
    help="Number of days ahead to fetch events for.",
)
@click.option(
    "--subject",
    default=settings.email_subject,
    help="Subject line for the email.",
)
@click.option(
    "--recipient-emails",
    "--to",
    default=settings.recipient_emails,
    help="Comma-separated list of recipient email addresses.",
)
@click.option(
    "--web",
    is_flag=True,
    help="View email in web browser.",
)
def main(calendar_id: str, days: int, subject: str, recipient_emails: str, web: bool):
    events_by_day = get_events(calendar_id, days)
    html_body = render_email(events_by_day)
    if web:
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_body)
            webbrowser.open(f'file://{f.name}')
    else:
        _ = send_email(
            subject=subject,
            html_body=html_body,
            to_addresses=[email.strip() for email in recipient_emails.split(",")],
            email_from=settings.email_from or settings.email_username,
        )

if __name__ == "__main__":
    main()
####