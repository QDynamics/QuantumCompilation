# PR Title

build: remove the unimplemented ucc console script

# PR Description

## Summary

This PR removes the unimplemented `ucc` console script from `pyproject.toml`.

The package currently declares:

```toml
[project.scripts]
ucc = "ucc.__main__:main"
```

but there is no implemented CLI entrypoint behind that declaration in the repository.

Instead of adding a new CLI at this time, this PR follows the review suggestion and removes the unsupported console script declaration so the published package metadata matches the actual project behavior.

## Changes

- remove the `ucc` console script entry from `pyproject.toml`

## Why this change

This keeps the package metadata accurate and avoids advertising a command-line interface that is not actually implemented or maintained.

I kept this PR intentionally narrow so it only addresses the packaging inconsistency.

## Validation

I verified locally with:

```bash
uv run pytest -q
uv build
```

The test suite passes, and the built wheel no longer exports a `ucc` console entrypoint.
