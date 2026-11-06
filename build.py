#!/usr/bin/env python3
"""Build two sing-box source rule sets from one editable, credential-free file."""
import argparse
import ipaddress
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
FIELDS = {"domain", "domain_suffix", "ip_cidr"}


def load_source():
    data = json.loads((ROOT / "rules.json").read_text())
    if set(data) != {"schema_version", "direct", "vpn"} or data["schema_version"] != 1:
        raise ValueError("Expected schema_version=1, direct and vpn only")
    for name in ("direct", "vpn"):
        section = data[name]
        if not isinstance(section, dict) or set(section) - FIELDS:
            raise ValueError(f"{name}: only domain, domain_suffix and ip_cidr are allowed")
        for field, values in section.items():
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise ValueError(f"{name}.{field}: expected a list of strings")
            if len(values) != len(set(values)):
                raise ValueError(f"{name}.{field}: duplicate entries")
            for value in values:
                if not value or value.strip() != value:
                    raise ValueError(f"{name}.{field}: empty value or surrounding whitespace")
                if field == "ip_cidr":
                    ipaddress.ip_network(value, strict=False)
                else:
                    host = value[1:] if field == "domain_suffix" and value.startswith(".") else value
                    if len(host) > 253 or any(
                        not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                        for label in host.split(".")
                    ):
                        raise ValueError(f"{name}.{field}: invalid domain: {value!r}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated files without changing them")
    args = parser.parse_args()
    source = load_source()
    for name in ("direct", "vpn"):
        # Separate rules preserve OR semantics between different matcher types.
        rules = [{field: values} for field, values in source[name].items() if values]
        result = {"version": 1, "rules": rules}
        content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        destination = ROOT / "dist" / f"{name}.json"
        if args.check:
            if not destination.exists() or destination.read_text() != content:
                raise SystemExit(f"Outdated generated file: {destination}")
        else:
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(content)
        print(f"{name}.json: {sum(map(len, source[name].values()))} entries; {len(rules)} matcher groups")


if __name__ == "__main__":
    main()
