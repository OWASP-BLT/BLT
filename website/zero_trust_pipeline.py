import hashlib
import json
import os
import secrets
import subprocess
import tarfile
import uuid

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from website.models import Issue, OrgEncryptionConfig

REPORT_TMP_DIR = getattr(settings, "REPORT_TMP_DIR", os.path.join(settings.BASE_DIR, "tmp_reports"))


def build_and_deliver_zero_trust_issue(issue: Issue, uploaded_files) -> None:
    """
    Synchronous zero-trust pipeline:

    1. Save uploaded files to an ephemeral directory.
    2. Build a tar.gz with metadata.json + files.
    3. Encrypt using the org's configuration.
    4. Compute SHA-256, send via email, update Issue metadata.
    5. Securely delete all temp files.
    """
    os.makedirs(REPORT_TMP_DIR, exist_ok=True)
    submission_id = str(uuid.uuid4())
    issue_tmp_dir = os.path.join(REPORT_TMP_DIR, submission_id)
    os.makedirs(issue_tmp_dir, exist_ok=True)

    try:
        # 1. Save uploaded files
        file_paths = []
        for f in uploaded_files:
            safe_name = os.path.basename(f.name)
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
        org = domain.organization if domain else None
        if org is None:
            raise RuntimeError("Zero-trust issue must be associated with a domain/organization.")

        try:
            org_config = OrgEncryptionConfig.objects.get(organization=org)
        except OrgEncryptionConfig.DoesNotExist:
            raise RuntimeError(f"No OrgEncryptionConfig for organization {org.name}")

        encrypted_path, method_used = _encrypt_artifact_for_org(org_config, tar_path, issue_tmp_dir, issue)

        # 4. Compute SHA-256 and send email
        artifact_sha256 = _compute_sha256(encrypted_path)
        _send_encrypted_issue_email(issue, org_config, encrypted_path, artifact_sha256, method_used)

        # Update Issue metadata only (no plaintext storage)
        issue.artifact_sha256 = artifact_sha256
        issue.encryption_method = method_used
        issue.delivery_method = "email:smtp"
        issue.delivery_status = "delivered"
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
    except Exception:
        issue.delivery_status = "failed"
        issue.save(update_fields=["delivery_status", "modified"])
        raise
    finally:
        _secure_delete_path(issue_tmp_dir)


def _build_tar_artifact(issue: Issue, file_paths, output_tar: str) -> None:
    metadata = {
        "issue_id": issue.id,
        "domain_url": issue.domain.url if issue.domain else None,
        "created_at": issue.created.isoformat() if issue.created else None,
        "label": issue.label,
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


def _encrypt_artifact_for_org(org_config: OrgEncryptionConfig, input_path: str, tmp_dir: str, issue: Issue):
    preferred = org_config.preferred_method

    # age
    if preferred == OrgEncryptionConfig.ENCRYPTION_METHOD_AGE and org_config.age_recipient:
        out = os.path.join(tmp_dir, "report_payload.tar.gz.age")
        cmd = [getattr(settings, "AGE_BINARY", "age"), "-r", org_config.age_recipient, "-o", out, input_path]
        subprocess.run(cmd, check=True)
        return out, OrgEncryptionConfig.ENCRYPTION_METHOD_AGE

    # OpenPGP
    if preferred == OrgEncryptionConfig.ENCRYPTION_METHOD_OPENPGP and org_config.pgp_fingerprint:
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
        subprocess.run(cmd, check=True)
        return out, OrgEncryptionConfig.ENCRYPTION_METHOD_OPENPGP

    # Fallback: symmetric 7z with random password (password must be OOB)
    out = os.path.join(tmp_dir, "report_payload.7z")
    password = secrets.token_urlsafe(32)
    cmd = [getattr(settings, "SEVENZ_BINARY", "7z"), "a", "-mhe=on", f"-p{password}", out, input_path]
    subprocess.run(cmd, check=True)
    _deliver_password_oob(org_config, issue.id, password)
    return out, OrgEncryptionConfig.ENCRYPTION_METHOD_SYM_7Z


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
):
    subject = f"[VULN REPORT] Secure delivery for issue_id: {issue.id}"
    body = f"""Hello {org_config.organization.name} security/contact team,

Attached is an encrypted vulnerability disclosure package for {org_config.organization.name}.

Issue ID: {issue.id}
Artifact SHA-256: {artifact_sha256}
Encryption: {encryption_method}
Delivery method: email:smtp

Please confirm receipt by replying to this message or by signing a short receipt
that includes the issue_id and artifact_sha256.

If you need the password for a symmetric archive, it has been delivered out-of-band
to the contact you provided.

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
    email.send(fail_silently=False)


def _deliver_password_oob(org_config: OrgEncryptionConfig, issue_id: int, password: str):
    """
    Placeholder hook: integrate with OOB channel (SMS/Signal/second email/etc.).
    Do NOT store the password in the database or logs.
    """
    # TODO: integrate with real OOB mechanism; for now, this is intentionally a no-op.
    pass


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
    try:
        length = os.path.getsize(path)
        with open(path, "wb") as f:
            f.write(b"\x00" * length)
        os.remove(path)
    except Exception:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
