"""
Zero-Trust Vulnerability Reporting Pipeline

SECURITY REQUIREMENTS:
- This module handles sensitive PoC files and vulnerability details
- MUST NOT be tracked by analytics (Google Analytics, Mouseflow, etc.)
- MUST NOT send data to Sentry (filtered in settings.py)
- MUST NOT log file content or request bodies
- API-only endpoint (no template rendering with tracking scripts)

If adding a web UI in the future:
- Exclude zero-trust pages from analytics tracking
- Use separate base template without analytics scripts
- Verify Sentry before_send filter is active
"""
import hashlib
import json
import logging
import os
import re
import string
import subprocess
import tarfile
import tempfile
import unicodedata
import uuid
from typing import List, Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.core.mail import EmailMessage
from django.utils import timezone

from website.models import Issue, OrgEncryptionConfig

logger = logging.getLogger(__name__)
REPORT_TMP_DIR = getattr(settings, "REPORT_TMP_DIR", os.path.join(settings.BASE_DIR, "tmp_reports"))


def _validate_age_recipient(recipient: str) -> bool:
    """Validate age recipient format (age1... or ssh-ed25519/rsa key)."""
    if recipient.startswith("age1"):
        return bool(re.match(r"^age1[a-z0-9]{58}$", recipient))

    # Validate SSH public keys in authorized_keys-style "type base64 [comment]" format.
    if recipient.startswith(("ssh-ed25519 ", "ssh-rsa ")):
        parts = recipient.split(" ", 2)
        if len(parts) < 2:
            return False
        key_type, key_b64 = parts[0], parts[1]
        if key_type not in ("ssh-ed25519", "ssh-rsa"):
            return False
        # Base64-encoded key: standard character set plus up to two padding '=' chars.
        if not re.fullmatch(r"[A-Za-z0-9+/]+={0,2}", key_b64):
            return False
        # Require a minimum length to avoid trivially invalid keys.
        if len(key_b64) < 16:
            return False
        return True
    return False


def _validate_pgp_fingerprint(fingerprint: str) -> bool:
    """Validate PGP fingerprint is hexadecimal."""
    return bool(re.match(r"^[A-Fa-f0-9]{40}$|^[A-Fa-f0-9]{64}$", fingerprint))


def _sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent path traversal and other issues."""
    filename = os.path.basename(filename)
    filename = unicodedata.normalize("NFKD", filename)
    filename = "".join(c for c in filename if c not in ("\x00", "\r", "\n"))

    safe_chars = string.ascii_letters + string.digits + " .-_"
    filename = "".join(c if c in safe_chars else "_" for c in filename)
    filename = filename.strip(". ")
    if not filename:
        filename = f"upload_{uuid.uuid4().hex[:8]}"
    max_length = 255
    if len(filename) > max_length:
        base, ext = os.path.splitext(filename)
        if len(ext) > 32:
            ext = ext[:32]
        available = max_length - len(ext)
        if available <= 0:
            filename = filename[:max_length]
        else:
            filename = base[:available] + ext
    return filename


def build_and_deliver_zero_trust_issue(issue: Issue, uploaded_files: List[UploadedFile]) -> None:
    """
    Synchronous zero-trust pipeline:

    1. Save uploaded files to an ephemeral directory.
    2. Build a tar.gz with metadata.json + files.
    3. Encrypt using the org's configuration.
    4. Compute SHA-256, send via email, update Issue metadata.
    5. Securely delete all temp files.
    """

    MAX_FILE_SIZE = getattr(settings, "ZERO_TRUST_MAX_FILE_SIZE", 50 * 1024 * 1024)  # 50MB
    MAX_TOTAL_SIZE = getattr(settings, "ZERO_TRUST_MAX_TOTAL_SIZE", 100 * 1024 * 1024)  # 100MB
    MAX_FILES_COUNT = getattr(settings, "ZERO_TRUST_MAX_FILES", 10)

    # Validate file count
    if len(uploaded_files) > MAX_FILES_COUNT:
        raise ValueError(f"Maximum {MAX_FILES_COUNT} files allowed")

    # Validate file sizes during streaming
    total_size = 0
    for f in uploaded_files:
        file_size = getattr(f, "size", None)
        if file_size is None:
            raise ValueError("Unable to determine uploaded file size. Please try again with a smaller file.")
        if file_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File {f.name} exceeds maximum size of {MAX_FILE_SIZE / (1024*1024):.0f}MB"
            )
        total_size += file_size

    if total_size > MAX_TOTAL_SIZE:
        raise ValueError(
            f"Total upload size {total_size / (1024*1024):.1f}MB exceeds maximum {MAX_TOTAL_SIZE / (1024*1024):.0f}MB"
        )

    os.makedirs(REPORT_TMP_DIR, exist_ok=True)

    issue_tmp_dir = None

    try:
        # Use mkdtemp to avoid UUID collisions and ensure a fresh directory
        issue_tmp_dir = tempfile.mkdtemp(prefix=f"issue_{issue.id}_", dir=REPORT_TMP_DIR)

        # 1. Save uploaded files with sanitized, collision-safe names
        file_paths: List[str] = []
        used: set = set()

        for f in uploaded_files:
            safe_name = _sanitize_filename(f.name)

            # Handle duplicate filenames by appending counter
            if safe_name in used:
                name_parts = os.path.splitext(safe_name)
                counter = 1
                while f"{name_parts[0]}_{counter}{name_parts[1]}" in used:
                    counter += 1
                safe_name = f"{name_parts[0]}_{counter}{name_parts[1]}"

            used.add(safe_name)
            dest_path = os.path.join(issue_tmp_dir, safe_name)

            with open(dest_path, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            file_paths.append(dest_path)

        # 2. Build tar.gz with metadata.json
        tar_path = os.path.join(issue_tmp_dir, "report_payload.tar.gz")
        _build_tar_artifact(issue, file_paths, tar_path)

        # 3. Encrypt according to org config
        domain = issue.domain
        org = getattr(domain, "organization", None) if domain else None
        if org is None:
            raise RuntimeError("Zero-trust issue must be associated with a domain/organization.")

        try:
            org_config = OrgEncryptionConfig.objects.get(organization=org)
        except OrgEncryptionConfig.DoesNotExist:
            raise RuntimeError(f"No OrgEncryptionConfig for organization {org.name}")

        encrypted_path, method_used = _encrypt_artifact_for_org(org_config, tar_path, issue_tmp_dir, issue)

        # 4. Compute SHA-256 and send email
        artifact_sha256 = _compute_sha256(encrypted_path)
        delivery_status = _send_encrypted_issue_email(issue, org_config, encrypted_path, artifact_sha256, method_used)

        issue.artifact_sha256 = artifact_sha256
        issue.encryption_method = method_used
        issue.delivery_method = "email:smtp"
        issue.delivery_status = delivery_status
        issue.delivered_at = timezone.now()
        issue.save(
            update_fields=[
                "artifact_sha256",
                "encryption_method",
                "delivery_method",
                "delivery_status",
                "delivered_at",
                "modified",
            ]
        )
    except Exception as e:
        issue.delivery_status = "failed"
        issue.save(update_fields=["delivery_status", "modified"])
        logger.error(
            f"Zero-trust pipeline failed for issue {issue.id}: {str(e)}",
            exc_info=True,
            extra={"issue_id": issue.id, "domain": issue.domain.url if issue.domain else None},
        )
        raise
    finally:
        if issue_tmp_dir is not None:
            _secure_delete_path(issue_tmp_dir)


def _build_tar_artifact(issue: Issue, file_paths, output_tar: str) -> None:
    """
    Build a compressed tarball containing metadata.json and uploaded files.
    The metadata.json is created temporarily and removed after archiving.
    """
    # Get human-readable label text
    label_text = None
    if issue.label is not None:
        try:
            # Issue.labels is a tuple of (value, display_name) pairs
            label_text = dict(Issue.labels).get(issue.label, str(issue.label))
        except (AttributeError, KeyError):
            label_text = str(issue.label)
    metadata = {
        "issue_id": issue.id,
        "domain_url": issue.domain.url if issue.domain else None,
        "created_at": issue.created.isoformat() if issue.created else None,
        "label": label_text,
        "label_code": issue.label,
        "note": "Zero-trust issue. Metadata only; full details in attached files.",
    }
    meta_path = os.path.join(os.path.dirname(output_tar), "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    with tarfile.open(output_tar, "w:gz") as tar:
        tar.add(meta_path, arcname="metadata.json")
        for p in file_paths:
            tar.add(p, arcname=os.path.basename(p))

    os.remove(meta_path)


def _encrypt_artifact_for_org(
    org_config: OrgEncryptionConfig, input_path: str, tmp_dir: str, issue: Issue
) -> Tuple[str, str]:
    """
    Encrypt the artifact using org's preferred method.
    """
    preferred = org_config.preferred_method

    # age
    if preferred == OrgEncryptionConfig.ENCRYPTION_METHOD_AGE and org_config.age_recipient:
        if not _validate_age_recipient(org_config.age_recipient):
            raise ValueError(f"Invalid age recipient format: {org_config.age_recipient}")
        out = os.path.join(tmp_dir, "report_payload.tar.gz.age")
        cmd = [getattr(settings, "AGE_BINARY", "age"), "-r", org_config.age_recipient, "-o", out, input_path]
        try:
            subprocess.run(cmd, check=True, timeout=300, capture_output=True, shell=False)
        except subprocess.TimeoutExpired as e:
            logger.error(f"Age encryption timed out for issue {issue.id} after {e.timeout} seconds", exc_info=True)
            raise RuntimeError(f"Encryption timed out after {e.timeout} seconds")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Age encryption failed for issue {issue.id}, return code: {e.returncode}",
                exc_info=True,
                extra={"stderr": e.stderr.decode("utf-8", errors="replace") if e.stderr else None},
            )
            raise RuntimeError(
                f"Encryption failed: {e.stderr.decode('utf-8', errors='replace') if e.stderr else 'Unknown error'}"
            )
        return out, OrgEncryptionConfig.ENCRYPTION_METHOD_AGE

    # OpenPGP
    if preferred == OrgEncryptionConfig.ENCRYPTION_METHOD_OPENPGP and org_config.pgp_fingerprint:
        if not _validate_pgp_fingerprint(org_config.pgp_fingerprint):
            raise ValueError(f"Invalid PGP fingerprint format: {org_config.pgp_fingerprint}")
        out = os.path.join(tmp_dir, "report_payload.tar.gz.asc")
        cmd = [
            getattr(settings, "GPG_BINARY", "gpg"),
            "--encrypt",
            "--armor",
            "--recipient",
            org_config.pgp_fingerprint,
            "--output",
            out,
            input_path,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=300, capture_output=True, shell=False)
        except subprocess.TimeoutExpired as e:
            logger.error(f"OpenPGP encryption timed out for issue {issue.id} after {e.timeout} seconds", exc_info=True)
            raise RuntimeError(f"Encryption timed out after {e.timeout} seconds")
        except subprocess.CalledProcessError as e:
            logger.error(
                f"OpenPGP encryption failed for issue {issue.id}, return code: {e.returncode}",
                exc_info=True,
                extra={"stderr": e.stderr.decode("utf-8", errors="replace") if e.stderr else None},
            )
            raise RuntimeError(
                f"Encryption failed: {e.stderr.decode('utf-8', errors='replace') if e.stderr else 'Unknown error'}"
            )
        return out, OrgEncryptionConfig.ENCRYPTION_METHOD_OPENPGP

    # No valid method configured
    raise RuntimeError(
        f"Organization {org_config.organization.name} has no valid encryption method configured. "
        f"Please configure Age or OpenPGP encryption."
    )


def _compute_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _send_encrypted_issue_email(
    issue: Issue,
    org_config: OrgEncryptionConfig,
    encrypted_path: str,
    artifact_sha256: str,
    encryption_method: str,
) -> str:
    subject = f"[VULN REPORT] Secure delivery for issue_id: {issue.id}"
    body = f"""Hello {org_config.organization.name} security/contact team,

Attached is an encrypted vulnerability disclosure package for {org_config.organization.name}.

Issue ID: {issue.id}
Artifact SHA-256: {artifact_sha256}
Encryption: {encryption_method}
Delivery method: email:smtp

Please confirm receipt by replying to this message or by signing a short receipt
that includes the issue_id and artifact_sha256.

Regards,
{getattr(settings, "PROJECT_NAME", "BLT")} Disclosure Service
"""

    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.EMAIL_TO_STRING,
        to=[org_config.contact_email],
    )
    email.attach_file(encrypted_path)
    try:
        email.send(fail_silently=False)
        return "delivered"
    except Exception as e:
        logger.error(f"Email delivery failed for issue {issue.id} to {org_config.contact_email}", exc_info=True)
        return "encryption_success_delivery_failed"


def _secure_delete_path(path: str) -> None:
    if not os.path.exists(path):
        return
    if os.path.isfile(path):
        _secure_delete_file(path)
        return

    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            _secure_delete_file(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(path)


def _secure_delete_file(path: str) -> None:
    """
    Attempt basic secure deletion by overwriting with zeros before removal.

    WARNING: This is NOT cryptographically secure deletion on modern systems:
    - Copy-on-write filesystems (btrfs, ZFS) may preserve data
    - SSDs with wear-leveling don't overwrite in place
    - Encrypted filesystems already protect data at rest

    This provides defense-in-depth by clearing RAM buffers and preventing
    simple file recovery, but should not be relied upon as the sole protection.
    """
    try:
        length = os.path.getsize(path)
        with open(path, "wb") as f:
            f.write(b"\x00" * length)
        os.remove(path)
    except FileNotFoundError:
        # File already removed by the time we tried to overwrite/delete it.
        logger.debug("Secure delete: file %s already removed, ignoring.", path)
    except Exception:
        # Overwrite or initial delete failed for some other reason; log and attempt best-effort removal.
        logger.warning("Secure delete failed for %s; attempting best-effort removal.", path, exc_info=True)
        try:
            os.remove(path)
        except FileNotFoundError:
            logger.debug("Secure delete fallback: file %s already removed, ignoring.", path)
        except Exception:
            logger.warning("Secure delete fallback removal failed for %s.", path, exc_info=True)
