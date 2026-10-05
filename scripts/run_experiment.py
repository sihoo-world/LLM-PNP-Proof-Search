"""Convenience wrapper; install the project with pip -e first."""

import sys
from pnp_search.cli import main

if __name__ == "__main__":
    main(["run", *sys.argv[1:]])

