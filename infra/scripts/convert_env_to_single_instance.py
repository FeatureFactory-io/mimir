#!/usr/bin/env python3
"""Strip LoadBalanced-only EB option settings for SingleInstance migration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_LIVE_PATH = Path(__file__).resolve().parent.parent / "eb_live_platform_settings.json"

_SKIP_NS_PREFIXES = ("aws:elbv2:", "aws:elasticbeanstalk:environment:process:")
_SKIP_OPTIONS = frozenset({
    ("aws:elasticbeanstalk:environment", "LoadBalancerType"),
    ("aws:elasticbeanstalk:environment", "LoadBalancerIsShared"),
    ("aws:ec2:vpc", "ELBScheme"),
    ("aws:ec2:vpc", "ELBSubnets"),
})


def convert_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Return platform rows suitable for ``EnvironmentType=SingleInstance``."""
    out: list[dict[str, str]] = []
    for row in rows:
        ns = row["namespace"]
        opt = row["option_name"]
        if ns.startswith(_SKIP_NS_PREFIXES):
            continue
        if (ns, opt) in _SKIP_OPTIONS:
            continue
        if ns == "aws:elasticbeanstalk:environment" and opt == "EnvironmentType":
            row = {**row, "value": "SingleInstance"}
        out.append(row)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "envs",
        nargs="+",
        help="EB environment keys in eb_live_platform_settings.json (e.g. mimir-idle)",
    )
    args = parser.parse_args()

    data = json.loads(_LIVE_PATH.read_text())
    for env in args.envs:
        if env not in data:
            raise SystemExit(f"Unknown env key: {env}")
        data[env] = convert_rows(data[env])

    _LIVE_PATH.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Converted {', '.join(args.envs)} to SingleInstance in {_LIVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
