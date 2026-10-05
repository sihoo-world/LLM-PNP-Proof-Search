# Small formal checks

This independent Lean project pins Lean 4 and Mathlib to v4.24.0. The upstream
[Mathlib toolchain at that tag](https://github.com/leanprover-community/mathlib4/blob/v4.24.0/lean-toolchain)
specifies that Lean version. The committed Boolean example uses only Lean core;
Mathlib is an available dependency for subsequent finite combinatorics.

Install Lean using its [official instructions](https://lean-lang.org/install/),
then initialize dependencies from this directory:

```sh
lake update
lake exe cache get
lake build
lake env lean PNPResearch/Basic.lean
```

Keep the generated `lake-manifest.json` in a reproducibility snapshot to pin
transitive dependencies. The first dependency setup needs network access and
can be much larger than the Python MVP. An unavailable toolchain, missing
dependency, timeout, or nonzero return code must remain an unsuccessful check.

`PNPResearch.bool_and_comm` checks a small Boolean identity by exhausting its
four cases. It is an established elementary fact, not a novel lower bound.
`function_and_comm` lifts the result by function extensionality. Neither theorem
proves a measure inequality or an asymptotic circuit lower bound.

For the core-only smoke check, use the separate configuration without fetching
or compiling Mathlib:

```sh
lake -f lakefile.core.toml env lean PNPResearch/Basic.lean
```

This deliberately proves only the core Boolean lemmas. It does not validate
the main Mathlib dependency installation. The core configuration stores its
manifest in `.lake/core-manifest.json`; the Mathlib project uses the separate
default `lake-manifest.json`.

The Python integration must use a trusted template, run `lake env lean`, and
save its source and process result. Model-provided proof text is not executable
input in the MVP. Require the expected theorem and reject admitted proofs or
unreviewed axioms. Compiler success alone is insufficient when an unrelated
theorem was substituted. Record whether the formal statement faithfully
represents the candidate as a separate review outcome.
