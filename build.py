#!/usr/bin/env python3
"""Build shared and mobile-specific rule sets from a credential-free source."""
import argparse
import ipaddress
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
FIELDS = {"domain", "domain_suffix", "ip_cidr"}
SECTIONS = ("direct", "vpn", "mobile_direct", "mobile_kosmo")


def entries(section):
    return {(field, value) for field, values in section.items() for value in values}


def covers(suffix, host):
    return host.endswith(suffix) if suffix.startswith('.') else host == suffix or host.endswith('.' + suffix)


def overlaps(first, second):
    left_type, left = first
    right_type, right = second
    if left_type not in {"domain", "domain_suffix"} or right_type not in {"domain", "domain_suffix"}:
        return False
    left, right = left.lower(), right.lower()
    if left_type == right_type == "domain":
        return left == right
    if left_type == "domain":
        return covers(right, left)
    if right_type == "domain":
        return covers(left, right)
    left, right = left.lstrip('.'), right.lstrip('.')
    return covers(left, right) or covers(right, left)


def load_source():
    data = json.loads((ROOT / "rules.json").read_text())
    if set(data) != {"schema_version", *SECTIONS} or data["schema_version"] != 2:
        raise ValueError("Expected schema_version=2 and direct/vpn/mobile_direct/mobile_kosmo")
    for name in SECTIONS:
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
    mobile_direct = entries(data["mobile_direct"])
    mobile_kosmo = entries(data["mobile_kosmo"])
    if mobile_direct & mobile_kosmo:
        raise ValueError("Mobile Direct and Mobile Kosmo contain the same entry")
    if mobile_direct | mobile_kosmo != entries(data["direct"]):
        raise ValueError("Every manual Direct entry must have exactly one mobile destination")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check generated files without changing them")
    args = parser.parse_args()
    source = load_source()
    registry = json.loads((ROOT / "sources/operator-registry.json").read_text())
    matchers = registry["matchers"]
    if registry["schema_version"] != 1 or set(matchers) - {"domain_suffix", "domain"}:
        raise ValueError("Invalid registry snapshot")
    outputs = {name.replace('_', '-'): source[name] for name in SECTIONS}
    outputs["mobile-registry-direct"] = matchers
    protected = entries(source["mobile_kosmo"]) | entries(source["vpn"])
    exclusions = []
    allowed = {}
    for field, values in matchers.items():
        allowed[field] = []
        for value in values:
            if any(overlaps((field, value), item) for item in protected):
                exclusions.append({"field": field, "value": value})
            else:
                allowed[field].append(value)
    # Personal mobile choices remain separate in rules.json. The published
    # Mobile Direct list also includes the entire maintained upstream category.
    outputs["mobile-direct"] = {
        field: list(dict.fromkeys(source["mobile_direct"].get(field, []) + allowed.get(field, [])))
        for field in sorted(set(source["mobile_direct"]) | set(allowed))
    }
    for name, section in outputs.items():
        # Separate rules preserve OR semantics between different matcher types.
        rules = [{field: values} for field, values in section.items() if values]
        result = {"version": 1, "rules": rules}
        content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        destination = ROOT / "dist" / f"{name}.json"
        if args.check:
            if not destination.exists() or destination.read_text() != content:
                raise SystemExit(f"Outdated generated file: {destination}")
        else:
            destination.parent.mkdir(exist_ok=True)
            destination.write_text(content)
        print(f"{name}.json: {sum(map(len, section.values()))} entries; {len(rules)} matcher groups")
    status = {k: v for k, v in registry.items() if k != "matchers"}
    status["rule_count"] = sum(map(len, matchers.values()))
    status["personal_priority_exclusions"] = exclusions
    status["mobile_direct_rule_count"] = sum(map(len, outputs["mobile-direct"].values()))
    path = ROOT / "dist/mobile-registry-status.json"
    content = json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if path.read_text() != content:
            raise SystemExit("Outdated registry status")
    else:
        path.write_text(content)


if __name__ == "__main__":
    main()
