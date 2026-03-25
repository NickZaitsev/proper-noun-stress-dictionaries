#!/usr/bin/env python3

import argparse
import ast
from pathlib import Path
from typing import Dict, Tuple


def load_python_dict(path: Path) -> Tuple[str, Dict[str, str]]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in module.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        value = ast.literal_eval(node.value)
        if isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
            return target.id, value
    raise ValueError(f"Could not load a string-to-string dict from {path}")


def write_python_dict(path: Path, variable_name: str, data: Dict[str, str]) -> None:
    items = sorted(data.items(), key=lambda item: item[0].lower())
    lines = [f"{variable_name} = {{"]
    for key, value in items:
        lines.append(f"    {key!r}: {value!r},")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create unique proper-noun dictionary layers without overlaps.")
    parser.add_argument("output_dir", type=Path, help="Directory containing the proper noun dictionaries")
    args = parser.parse_args()

    output_dir = args.output_dir

    priority_name, priority = load_python_dict(output_dir / "all_proper_nouns_priority_full_names.py")
    single_name, single = load_python_dict(output_dir / "all_proper_nouns_observed_single_variant.py")
    frequent_name, frequent = load_python_dict(output_dir / "all_proper_nouns_observed_most_frequent.py")

    priority_unique = dict(priority)
    priority_keys = set(priority_unique)

    single_unique = {key: value for key, value in single.items() if key not in priority_keys}
    single_keys = set(single_unique)

    frequent_unique = {
        key: value
        for key, value in frequent.items()
        if key not in priority_keys and key not in single_keys
    }

    write_python_dict(
        output_dir / "all_proper_nouns_priority_full_names_unique.py",
        f"{priority_name}_unique",
        priority_unique,
    )
    write_python_dict(
        output_dir / "all_proper_nouns_observed_single_variant_unique.py",
        f"{single_name}_unique",
        single_unique,
    )
    write_python_dict(
        output_dir / "all_proper_nouns_observed_most_frequent_unique.py",
        f"{frequent_name}_unique",
        frequent_unique,
    )

    print(f"priority_unique={len(priority_unique)}")
    print(f"single_unique={len(single_unique)}")
    print(f"most_frequent_unique={len(frequent_unique)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
