"""Convenience wrapper for saved-candidate checks."""

import sys
from pnp_search.cli import main

if __name__ == "__main__":
    main(["verify", *sys.argv[1:]])

