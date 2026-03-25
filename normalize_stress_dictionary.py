#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import Optional, Sequence

from extract_proper_noun_stress import load_python_dict, write_python_dict


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize a generated stress dictionary Python file.")
    parser.add_argument("input_path", type=Path, help="Path to a *_observed.py file")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Optional output file path. Defaults to in-place normalization.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    variable_name, data = load_python_dict(args.input_path)
    output_path = args.output_path or args.input_path
    write_python_dict(output_path, variable_name, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
