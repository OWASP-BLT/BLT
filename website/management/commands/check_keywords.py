import re

import requests
from bs4 import BeautifulSoup
from django.core.mail import send_mail
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Monitor


class Command(LoggedBaseCommand):
    help = "Checks for keywords in monitored URLs"

    def handle(self, *args, **options):
        monitors = Monitor.objects.all()
        if not monitors:
            self.stdout.write(self.style.WARNING("No monitors found."))
            return

        # Allow optional debug output via environment/flag later if needed
        EMAIL_REGEX = re.compile(r"(?:mailto:)?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)

        for monitor in monitors:
            try:
                self.stdout.write(f"Checking {monitor.url}")
                response = requests.get(monitor.url, timeout=15)
                self.stdout.write(f"    HTTP {response.status_code}; content length {len(response.content or b'')}")
                response.raise_for_status()

                page_text = BeautifulSoup(response.text or "", "html.parser").get_text()

                # Email detection (single pass, deduplicated)
                found_emails = []
                try:
                    # Search the RAW HTML (response.text)
                    found_emails = list(dict.fromkeys(m.group(1) for m in EMAIL_REGEX.finditer(response.text or "")))

                except Exception:
                    found_emails = []

                if found_emails:
                    self.stdout.write(self.style.SUCCESS(f"[PII Found] {monitor.url}: {len(found_emails)} email(s) detected"))
                    email_note = f"Found email(s): {', '.join(found_emails)} "
                    if getattr(monitor, "notes", None):
                        monitor.notes = f"{monitor.notes}{email_note}"
                    else:
                        monitor.notes = email_note
                    monitor.save()
                else:
                    self.stdout.write(f"    No emails detected on {monitor.url}")

                # Keyword presence check (case-insensitive / regex support).
                reachable = response.status_code and response.status_code < 400
                if not monitor.keyword or not str(monitor.keyword).strip():
                    # No keyword configured: consider service UP if site is reachable
                    new_status = "UP" if reachable else "DOWN"
                    self.stdout.write(f"    No keyword configured; reachable={reachable} -> status {new_status}")
                else:
                    keyword = str(monitor.keyword).strip()
                    # regex support: /pattern/ (case-insensitive)
                    if keyword.startswith("/") and keyword.endswith("/") and len(keyword) > 1:
                        pattern = keyword[1:-1]
                        try:
                            found = bool(re.search(pattern, page_text, re.IGNORECASE))
                        except re.error:
                            found = False
                            self.stdout.write(f"    Invalid regex pattern: '{pattern}'")
                    else:
                        found = keyword.lower() in page_text.lower()
                    new_status = "UP" if found else "DOWN"
                    if not found:
                        self.stdout.write(f"    Keyword not found: '{keyword}'")
                        try:
                            snippet = " ".join(page_text.strip().split())[:500]
                        except Exception:
                            snippet = page_text[:200]
                        self.stdout.write(f"    Page snippet: {snippet!s}")
                        found_in_html = keyword.lower() in (response.text or "").lower()
                        self.stdout.write(f"    Found in raw HTML: {found_in_html}")

                if monitor.status != new_status:
                    old = monitor.status
                    monitor.status = new_status
                    monitor.save()
                    self.stdout.write(f"    Status changed {old} -> {new_status}")
                    user = monitor.user
                    self.notify_user(user.username, monitor.url, user.email, new_status)

                monitor.last_checked_time = timezone.now()
                monitor.save()

                self.stdout.write(self.style.SUCCESS(f"Monitoring {monitor.url}: status {monitor.status}"))
            except requests.exceptions.Timeout:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: network request timed out"))
                monitor.status ="DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
            except requests.exceptions.ConnectionError:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: network connection failed"))
                monitor.status ="DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
            except requests.exceptions.HTTPError:
                self.stderr.write(
                    self.style.ERROR(f"Error monitoring {monitor.url}: received non-success HTTP response")
                )
                monitor.status ="DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
            except requests.exceptions.RequestException:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: network request failed"))
                monitor.status ="DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
            except Exception:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error monitoring {monitor.url}: unexpected error during check (parsing, database save, or internal processing). "
                        "Check container logs, verify network connectivity, HTML parsing results, and database configuration."
                    )
                    monitor.status ="DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                )

    def notify_user(self, username, website, email, status):
        subject = f"Website Status Update: {website} is {status}"
        message = f"Dear {username},\n\nThe website '{website}' you are monitoring is currently {status}."

        send_mail(
            subject,
            message,
            None,
            [email],
            fail_silently=False,
        )
