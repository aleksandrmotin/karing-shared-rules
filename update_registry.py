#!/usr/bin/env python3
"""Convert a complete upstream GeoSite category; never execute upstream code."""
import argparse
import datetime
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = "https://github.com/GrimbirdUsers/ru-routing-dat"
CATEGORY = "category-ru-whitelist"


def collect(source):
    data_dir = source / "data-geosite"
    visited, active = set(), set()
    result = {"domain_suffix": set(), "domain": set()}

    def read(name):
        if not re.fullmatch(r"[a-z0-9-]+", name):
            raise ValueError(f"Invalid category name: {name!r}")
        if name in active:
            raise ValueError(f"Include cycle: {name}")
        if name in visited:
            return
        if len(visited) >= 100:
            raise ValueError("Too many included categories")
        visited.add(name)
        active.add(name)
        text = (data_dir / name).read_text()
        if len(text) > 1000000:
            raise ValueError("Source category too large")
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("include:"):
                read(line[8:])
                continue
            kind, sep, host = line.partition(":")
            if not sep or kind not in {"domain", "full"}:
                raise ValueError(f"Unsupported upstream rule: {line!r}")
            if len(host) > 253 or any(not re.fullmatch(
                r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part
            ) for part in host.split(".")):
                raise ValueError(f"Invalid upstream hostname: {host!r}")
            # Preserve the upstream service TLD .yandex and existing .psk entry,
            # but stop if an update introduces a catch-all TLD such as ru/com.
            if "." not in host and host not in {"yandex", "psk"}:
                raise ValueError(f"Unexpected broad suffix: {host!r}")
            result["domain_suffix" if kind == "domain" else "domain"].add(host)
        active.remove(name)

    read(CATEGORY)
    count = sum(map(len, result.values()))
    if not 100 <= count <= 20000:
        raise ValueError(f"Unexpected registry size: {count}")
    for anchor in ("wildberries.ru", "ozon.ru", "yandex.ru", "okko.tv"):
        if anchor not in result["domain_suffix"]:
            raise ValueError(f"Missing core service: {anchor}")
    return {k: sorted(v) for k, v in result.items() if v}, sorted(visited)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    matchers, categories = collect(args.source_dir)
    revision = subprocess.check_output(
        ["git", "-C", str(args.source_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    committed = subprocess.check_output(
        ["git", "-C", str(args.source_dir), "log", "-1", "--format=%cI"], text=True
    ).strip()
    snapshot = {
        "schema_version": 1,
        "source_repository": UPSTREAM,
        "source_revision": revision,
        "source_committed_at": committed,
        "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "category": CATEGORY,
        "classification": "community_routing_dataset_not_official_operator_registry",
        "included_categories": categories,
        "matchers": matchers,
    }
    target = ROOT / "sources" / "operator-registry.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    print(f"Registry: {sum(map(len, matchers.values()))} rules from {len(categories)} categories at {revision}")


if __name__ == "__main__":
    main()
