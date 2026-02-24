from urllib.parse import urlparse

try:
    import dns.resolver
except Exception:  # pragma: no cover - graceful fallback when dependency is unavailable
    dns = None


DNS_LOOKUP_TIMEOUT_SECONDS = 3.0


def _extract_hostname(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return ""

    if "://" not in value:
        value = f"https://{value}"

    parsed = urlparse(value)
    return (parsed.hostname or "").lower()


def _lookup_txt_records(name):
    if dns is None:
        return []

    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=DNS_LOOKUP_TIMEOUT_SECONDS)
        records = []
        for answer in answers:
            record = answer.to_text().strip('"')
            if record:
                records.append(record)
        return records
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout):
        return []


def _lookup_dnskey_records(name):
    if dns is None:
        return False

    try:
        answers = dns.resolver.resolve(name, "DNSKEY", lifetime=DNS_LOOKUP_TIMEOUT_SECONDS)
        return len(answers) > 0
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout):
        return False


def get_domain_dns_posture(domain_name_or_url):
    hostname = _extract_hostname(domain_name_or_url)
    if not hostname:
        return {"domain": "", "spf": False, "dmarc": False, "dnssec": False}

    root_txt_records = _lookup_txt_records(hostname)
    dmarc_txt_records = _lookup_txt_records(f"_dmarc.{hostname}")

    has_spf = any(record.lower().startswith("v=spf1") for record in root_txt_records)
    has_dmarc = any(record.lower().startswith("v=dmarc1") for record in dmarc_txt_records)
    has_dnssec = _lookup_dnskey_records(hostname)

    return {"domain": hostname, "spf": has_spf, "dmarc": has_dmarc, "dnssec": has_dnssec}
