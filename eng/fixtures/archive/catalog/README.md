# Fixture catalog

CI tests typically build a synthetic mini-archive in tempfile (see `scripts/tests/test_catalog_api.py`).

To materialize a local fixture DB from copied sessions, export with an output_dir whose
`archive/` is this tree (parent of `research/`), e.g. `eng/fixtures`.

Live production always uses `<project>/archive/catalog/research_compare.sqlite`.
