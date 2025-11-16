import re
import ipaddress
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.core.mail import send_mail
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Monitor

# Compile email regex once at module level for efficiency
EMAIL_REGEX = re.compile(r"(?:mailto:)?([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", re.IGNORECASE)


class Command(LoggedBaseCommand):
    help = "Checks for keywords in monitored URLs"

    def is_safe_url(self, url):
        """Validate URL to prevent SSRF attacks by blocking private IPs and cloud metadata endpoints."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False

            # Resolve hostname to IP
            import socket
            try:
                ip = socket.gethostbyname(hostname)
            except socket.gaierror:
                self.stderr.write(f"    Cannot resolve hostname: {hostname}")
                return False

            ip_obj = ipaddress.ip_address(ip)

            # Block private IP ranges (RFC 1918, link-local, localhost, reserved)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                self.stderr.write(f"    Blocked private/reserved IP: {ip} for {hostname}")
                return False

            # Block cloud metadata endpoints
            if ip == "169.254.169.254":
                self.stderr.write(f"    Blocked cloud metadata endpoint: {ip}")
                return False

            return True
        except Exception as e:
            self.stderr.write(f"    URL validation error: {e}")
            return False

    def handle(self, *args, **options):
        monitors = Monitor.objects.all()
        if not monitors:
            self.stdout.write(self.style.WARNING("No monitors found."))
            return

        for monitor in monitors:
            try:
                self.stdout.write(f"Checking {monitor.url}")
                
                # Validate URL to prevent SSRF attacks
                if not self.is_safe_url(monitor.url):
                    self.stderr.write(self.style.ERROR(f"Unsafe URL blocked: {monitor.url}"))
                    old_status = monitor.status
                    monitor.status = "DOWN"
                    monitor.last_checked_time = timezone.now()
                    monitor.save(update_fields=["status", "last_checked_time"])
                    if old_status != "DOWN":
                        try:
                            self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                        except Exception as e:
                            self.stderr.write(f"    Failed to notify user: {e}")
                    continue
                
                response = requests.get(monitor.url, timeout=15)
                self.stdout.write(f"    HTTP {response.status_code}; content length {len(response.content or b'')}")
                response.raise_for_status()

                found_emails = []
                try:
                    # Search the RAW HTML (response.text)
                    found_emails = list(dict.fromkeys(m.group(1) for m in EMAIL_REGEX.finditer(response.text or "")))
                except (AttributeError, TypeError) as e:
                    self.stderr.write(f"    Email extraction error: {e}")
                    found_emails = []

                if found_emails:
                    self.stdout.write(
                        self.style.SUCCESS(f"[PII Found] {monitor.url}: {len(found_emails)} email(s) detected")
                    )

                    existing_notes = getattr(monitor, "notes", None) or ""
                    existing_emails_raw = set(re.findall(r"Found email\(s\): ([^;]+)", existing_notes))

                    existing_flat = set()
                    for email_list in existing_emails_raw:
                        existing_flat.update(e.strip() for e in email_list.split(","))

                    # Case-insensitive deduplication
                    existing_flat_lower = {e.lower() for e in existing_flat}
                    new_emails = [e for e in found_emails if e.lower() not in existing_flat_lower]
                    if new_emails:
                        email_note = f"Found email(s): {', '.join(new_emails)}; "
                        separator = " | " if existing_notes and not existing_notes.endswith((" ", ";")) else ""
                        monitor.notes = f"{existing_notes}{separator}{email_note}".strip()
                        monitor.save()
                else:
                    self.stdout.write(f"    No emails detected on {monitor.url}")

                # Keyword presence check (case-insensitive / regex support).
                reachable = bool(response.status_code and response.status_code < 400)
                if not monitor.keyword or not str(monitor.keyword).strip():
                    new_status = "UP" if reachable else "DOWN"
                    self.stdout.write(f"    No keyword configured; reachable={reachable} -> status {new_status}")
                else:
                    # Parse page text only when keyword is configured
                    page_text = BeautifulSoup(response.text or "", "html.parser").get_text()
                    keyword = str(monitor.keyword).strip()
                    is_regex = keyword.startswith("/") and keyword.endswith("/") and len(keyword) > 1
                    if is_regex:
                        pattern = keyword[1:-1]
                        try:
                            found = bool(re.search(pattern, page_text, re.IGNORECASE))
                        except re.error as e:
                            self.stderr.write(f"    Invalid regex pattern '{pattern}': {e}")
                            found = False
                    else:
                        pattern = None
                        found = keyword.lower() in page_text.lower()
                    new_status = "UP" if found else "DOWN"
                    if not found:
                        self.stdout.write(f"    Keyword not found: '{keyword}'")
                        try:
                            snippet = " ".join(page_text.strip().split())[:500]
                        except (AttributeError, TypeError):
                            snippet = page_text[:200]
                        # Redact email addresses from snippet to avoid logging PII
                        snippet = EMAIL_REGEX.sub("<email redacted>", snippet)
                        self.stdout.write(f"    Page snippet: {snippet!s}")
                        if is_regex and pattern:
                            found_in_html = bool(re.search(pattern, response.text or "", re.IGNORECASE))
                        else:
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
                old_status = monitor.status
                monitor.status = "DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                if old_status != "DOWN":
                    try:
                        self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                    except Exception as e:
                        self.stderr.write(f"    Failed to notify user: {e}")
            except requests.exceptions.ConnectionError:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: network connection failed"))
                old_status = monitor.status
                monitor.status = "DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                if old_status != "DOWN":
                    try:
                        self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                    except Exception as e:
                        self.stderr.write(f"    Failed to notify user: {e}")
            except requests.exceptions.HTTPError:
                self.stderr.write(
                    self.style.ERROR(f"Error monitoring {monitor.url}: received non-success HTTP response")
                )
                old_status = monitor.status
                monitor.status = "DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                if old_status != "DOWN":
                    try:
                        self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                    except Exception as e:
                        self.stderr.write(f"    Failed to notify user: {e}")
            except requests.exceptions.RequestException:
                self.stderr.write(self.style.ERROR(f"Error monitoring {monitor.url}: network request failed"))
                old_status = monitor.status
                monitor.status = "DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                if old_status != "DOWN":
                    try:
                        self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                    except Exception as e:
                        self.stderr.write(f"    Failed to notify user: {e}")
            except Exception as e:  # noqa: BLE001 - broad catch required to prevent one bad monitor from aborting the entire command run
                self.stderr.write(
                    self.style.ERROR(
                        f"Error monitoring {monitor.url}: unexpected error during check - {type(e).__name__}: {e}. "
                        "This may indicate a parsing, database, or internal processing issue. Check container logs for details."
                    )
                )
                old_status = monitor.status
                monitor.status = "DOWN"
                monitor.last_checked_time = timezone.now()
                monitor.save(update_fields=["status", "last_checked_time"])
                if old_status != "DOWN":
                    try:
                        self.notify_user(monitor.user.username, monitor.url, monitor.user.email, "DOWN")
                    except Exception as notify_error:
                        self.stderr.write(f"    Failed to notify user: {notify_error}")

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
