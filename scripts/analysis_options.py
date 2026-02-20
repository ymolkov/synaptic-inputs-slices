#!/usr/bin/env python3
import os
from typing import Dict


def _default_paths(project_root: str):
    flags_path = os.path.join(project_root, "config", "analysis_flags_overrides.txt")
    return flags_path


def parse_flags_file(flags_path: str) -> Dict[str, str]:
    flags_map: Dict[str, str] = {}
    if not os.path.exists(flags_path):
        return flags_map
    with open(flags_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            basename, flag_str = line.split("=", 1)
            basename = basename.strip()
            flag_str = flag_str.strip()
            if basename and flag_str:
                flags_map[basename] = flag_str
    return flags_map


def get_flags_map(project_root: str, strip_q: bool = True) -> Dict[str, str]:
    # strip_q is kept for backward compatibility with existing callers.
    flags_path = _default_paths(project_root)
    return parse_flags_file(flags_path)


def resolve_flags(
    basename: str,
    flags_map: Dict[str, str],
    default_flags: str = "-f 25",
    infer_vc_from_name: bool = True,
) -> str:
    flags = flags_map.get(basename, default_flags).strip()
    if infer_vc_from_name and ("-V" in basename) and ("-vc" not in flags):
        flags += " -vc"
    return flags
