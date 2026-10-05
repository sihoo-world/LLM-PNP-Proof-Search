"""Convenience wrapper for candidate generation."""

import sys
from pnp_search.cli import main

if __name__ == "__main__":
    main(["generate", *sys.argv[1:]])

