import smtplib
import tempfile
import webbrowser
from collections import defaultdict
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

import click
from gcsa.google_calendar import GoogleCalendar
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings

creds = Path(__file__).parent / "creds" / "credentials.json"


def get_events(calendar_id: str, days: int, include_today: bool = False):
    day_offset = 1 if not include_today else 0
    gc = GoogleCalendar(credentials_path=creds)
    events = gc.get_events(
        calendar_id=calendar_id,
        time_min=datetime.today() + timedelta(days=day_offset),
        time_max=datetime.today() + timedelta(days=days),
        single_events=True,
        order_by="startTime",
    )
    grouped = defaultdict(list)
    for e in events:
        day = e.start.astimezone(ZoneInfo(settings.timezone)).date()
        e.start = e.start.astimezone(ZoneInfo(settings.timezone))
        e.end = e.end.astimezone(ZoneInfo(settings.timezone))
        grouped[day].append(e)
    return grouped


def render_email(events_by_day):
    env = Environment(
        loader=FileSystemLoader("templates"),
        autoescape=select_autoescape(["html", "xml"])
    )
    template = env.get_template("weekly-email.html.jinja2")
    return template.render(events_by_day=events_by_day)


def send_email(subject, html_body, to_addresses, email_from, dry_run=False):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = ", ".join(to_addresses)
    if dry_run is True:
        click.echo("DRY RUN: Email would be sent with the following details:")
        click.echo(f"Subject: {subject}")
        click.echo(f"From: {email_from}")
        click.echo(f"To: {', '.join(to_addresses)}")
        click.echo("Email body would be sent but not actually delivered.")
        return
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
    default=7,
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
@click.option("--include-today", is_flag=True, help="Include today's events. By default next day events only are displayed.")
@click.option(
    "--email",
    is_flag=True,
    help="Send email.",
)
@click.option(
    "--web",
    is_flag=True,
    help="View email in web browser.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print email details without sending.",
)
def main(calendar_id: str, days: int, subject: str, recipient_emails: str, include_today: bool, email: bool, web: bool, dry_run: bool):
    events_by_day = get_events(calendar_id, days, include_today=include_today)
    html_body = render_email(events_by_day)
    if email is True and web is True:
        raise click.UsageError("Cannot use --email and --web options together.")
    if web:
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(html_body)
            webbrowser.open(f'file://{f.name}')
    elif email:
        _ = send_email(
            subject=subject,
            html_body=html_body,
            to_addresses=[email.strip() for email in recipient_emails.split(",")],
            email_from=settings.email_from or settings.email_username,
            dry_run=dry_run
        )
    else:
        for day, events in sorted(events_by_day.items()):
            click.echo(f"{day.strftime('%A, %B %d, %Y')}:")
            for e in events:
                click.echo(f"  - {e.start.strftime('%Y-%m-%d %I:%M %p')} - {e.summary}")
            click.echo()

if __name__ == "__main__":
    main()
####