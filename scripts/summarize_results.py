"""Convenience wrapper for JSON and CSV summaries."""

import sys
from pnp_search.cli import main

if __name__ == "__main__":
    main(["summarize", *sys.argv[1:]])
