# Publishing to PyPI

The distribution name is `mmcli-dl`; the installed command is `mmcli`.

## Build & validate

```
uv build
uvx twine check dist/*
```

## Upload

Upload to TestPyPI first to verify the listing, then to PyPI:

```
uvx twine upload --repository testpypi dist/*   # dry run on TestPyPI
uvx twine upload dist/*                          # real upload to PyPI
```

`twine` prompts for credentials (use a PyPI API token as the password, username
`__token__`). Bump `version` in `pyproject.toml` before each release — PyPI
rejects re-uploading an existing version.
