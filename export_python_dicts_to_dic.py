#!/usr/bin/env python3

import argparse
from pathlib import Path
from typing import Optional, Sequence

from extract_proper_noun_stress import load_python_dict


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Python string-to-string dictionaries into .dic files with key=value lines."
    )
    parser.add_argument("input_dir", type=Path, help="Directory containing Python dictionary files")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to <input_dir>.dic",
    )
    return parser.parse_args(argv)


def default_output_dir(input_dir: Path) -> Path:
    return input_dir.with_name(f"{input_dir.name}.dic")


def write_dic_file(path: Path, data: dict[str, str]) -> None:
    lines = [f"{key}={value}" for key, value in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = args.input_dir

    if not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")

    output_dir = args.output_dir or default_output_dir(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    skipped = 0

    for input_path in sorted(input_dir.glob("*.py")):
        try:
            _, data = load_python_dict(input_path)
        except ValueError:
            skipped += 1
            print(f"skipped {input_path.name}: not a string-to-string dict assignment")
            continue

        output_path = output_dir / f"{input_path.stem}.dic"
        write_dic_file(output_path, data)
        converted += 1
        print(f"written {output_path}")

    print(f"converted={converted}")
    print(f"skipped={skipped}")
    return 0 if converted else 1


if __name__ == "__main__":
    raise SystemExit(main())
