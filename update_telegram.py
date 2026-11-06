#!/usr/bin/env python3
"""Publish validated Telegram CIDRs; a failed update must stop deployment."""
import argparse
import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
SOURCE = "https://core.telegram.org/resources/cidr.txt"
MAX_BYTES = 65536


def snapshot_due(last_commit_epoch, now_epoch):
    """Keep a verified source snapshot in Git at least every thirty days."""
    return last_commit_epoch is None or now_epoch - last_commit_epoch >= 30 * 86400


def parse_cidrs(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not 5 <= len(lines) <= 256:
        raise ValueError("Unexpected number of Telegram networks")
    networks = [ipaddress.ip_network(line, strict=True) for line in lines]
    if len(networks) != len(set(networks)):
        raise ValueError("Duplicate networks")
    if {net.version for net in networks} != {4, 6}:
        raise ValueError("Expected both IPv4 and IPv6 networks")
    for net in networks:
        if not net.is_global or net.prefixlen < (16 if net.version == 4 else 32):
            raise ValueError(f"Non-public or unexpectedly broad network: {net}")
    return [str(net) for net in networks]


def encode(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-file", type=Path, help="Validate a local source instead of downloading")
    parser.add_argument("--check", action="store_true", help="Validate existing generated files offline")
    args = parser.parse_args()
    destination = ROOT / "dist" / "telegram.json"
    status_path = ROOT / "dist" / "telegram-status.json"
    if args.check:
        data = json.loads(destination.read_text())
        cidrs = data["rules"][0]["ip_cidr"]
        canonical = {"version": 1, "rules": [{"ip_cidr": parse_cidrs("\n".join(cidrs))}]}
        if data != canonical:
            raise ValueError("Unexpected Telegram rule set structure")
        status = json.loads(status_path.read_text())
        if status["rule_set_sha256"] != hashlib.sha256(destination.read_bytes()).hexdigest():
            raise ValueError("Telegram status checksum mismatch")
        print(f"telegram.json: {len(cidrs)} validated networks")
        return
    if args.source_file:
        raw = args.source_file.read_bytes()
    else:
        request = urllib.request.Request(SOURCE, headers={"User-Agent": "karing-shared-rules/1"})
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status != 200 or response.url != SOURCE:
                raise ValueError("Unexpected Telegram source response or redirect")
            raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Telegram source is too large")
    cidrs = parse_cidrs(raw.decode("utf-8"))
    content = encode({"version": 1, "rules": [{"ip_cidr": cidrs}]})
    status = {
        "source": SOURCE,
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ipv4_networks": sum(ipaddress.ip_network(cidr).version == 4 for cidr in cidrs),
        "ipv6_networks": sum(ipaddress.ip_network(cidr).version == 6 for cidr in cidrs),
        "rule_set_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(content)
    status_path.write_text(encode(status))
    print(f"telegram.json: updated {len(cidrs)} networks from {SOURCE}")


if __name__ == "__main__":
    main()
