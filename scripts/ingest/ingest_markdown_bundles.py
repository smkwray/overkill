#!/usr/bin/env python3
"""Import GPT Pro markdown bundle files into research/input/gptpro."""

from __future__ import annotations

import sys

from overkill.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["ingest-markdown-bundles", *sys.argv[1:]]))

