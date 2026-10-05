"""Command-line interface for lupaxa.fortune."""

from __future__ import annotations

import argparse
import os
import random
import sys
from collections.abc import Sequence

from lupaxa.fortune.exceptions import DatasetError, FortuneError
from lupaxa.fortune.generator import FortuneGenerator
from lupaxa.fortune.models import CATEGORIES, Mode, list_categories
from lupaxa.fortune.render import render_fortune
from lupaxa.fortune.version import get_version


def build_parser() -> argparse.ArgumentParser:
    """Return the fortune-cookie argument parser."""
    parser = argparse.ArgumentParser(
        prog="fortune-cookie",
        description="Draw a developer fortune cookie.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"lupaxa-fortune {get_version()}",
    )
    parser.add_argument(
        "--categories",
        action="store_true",
        help="List ordinary categories and exit.",
    )
    parser.add_argument(
        "--category",
        choices=CATEGORIES,
        default=argparse.SUPPRESS,
        help="Limit a standard fortune to one ordinary category.",
    )
    parser.add_argument(
        "--count",
        type=_positive_int,
        default=argparse.SUPPRESS,
        help="How many fortunes to print. The default is 1.",
    )
    numbers = parser.add_mutually_exclusive_group()
    numbers.add_argument(
        "--numbers",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Show lucky numbers. This is the default.",
    )
    numbers.add_argument(
        "--no-numbers",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Hide lucky numbers.",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dark", action="store_true", default=argparse.SUPPRESS, help="Dark mode.")
    modes.add_argument(
        "--corporate",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Corporate mode.",
    )
    modes.add_argument(
        "--oracle",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Oracle mode.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Plain text without decorations.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=argparse.SUPPRESS,
        help="Integer seed for a repeatable result.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    try:
        return _run(argv)
    except KeyboardInterrupt:
        print("lupaxa-fortune: error: interrupted", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return _silence_broken_pipe()


def _run(argv: Sequence[str] | None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.categories:
        _reject_inspection_mix(parser, args)
        for name in list_categories():
            print(name)
        return 0

    mode = _mode(args)
    category = getattr(args, "category", None)
    if category is not None and mode != "standard":
        parser.error("a category cannot be combined with a special mode")

    include_numbers = not hasattr(args, "no_numbers")
    plain = hasattr(args, "plain")
    count = getattr(args, "count", 1)
    seed = getattr(args, "seed", None)
    generator = FortuneGenerator(rng=random.Random(seed) if seed is not None else random.Random())

    try:
        first = True
        for _ in range(count):
            fortune = generator.generate(
                category=category,
                mode=mode,
                include_numbers=include_numbers,
            )
            if not first:
                sys.stdout.write("\n")
            first = False
            sys.stdout.write(render_fortune(fortune, plain=plain) + "\n")
            sys.stdout.flush()
    except DatasetError as exc:
        print(f"lupaxa-fortune: error: {exc}", file=sys.stderr)
        return 1
    except FortuneError as exc:
        print(f"lupaxa-fortune: error: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        raise
    except OSError as exc:
        print(f"lupaxa-fortune: error: {exc}", file=sys.stderr)
        return 1
    return 0


def _mode(args: argparse.Namespace) -> Mode:
    if hasattr(args, "dark"):
        return "dark"
    if hasattr(args, "corporate"):
        return "corporate"
    if hasattr(args, "oracle"):
        return "oracle"
    return "standard"


def _reject_inspection_mix(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    flags = (
        ("category", "--category"),
        ("count", "--count"),
        ("numbers", "--numbers"),
        ("no_numbers", "--no-numbers"),
        ("dark", "--dark"),
        ("corporate", "--corporate"),
        ("oracle", "--oracle"),
        ("plain", "--plain"),
        ("seed", "--seed"),
    )
    present = [label for name, label in flags if hasattr(args, name)]
    if present:
        parser.error("--categories cannot be combined with generation options")


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("count must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("count must be a positive integer")
    return number


def _silence_broken_pipe() -> int:
    """Point stdout at ``/dev/null`` so process shutdown does not raise again."""
    try:
        fd = sys.stdout.fileno()
    except (AttributeError, OSError, ValueError):
        return 0
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        return 0
    try:
        os.dup2(devnull, fd)
    except OSError:
        return 0
    finally:
        os.close(devnull)
    return 0
