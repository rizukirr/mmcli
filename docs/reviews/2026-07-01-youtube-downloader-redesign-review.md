# Review — YouTube Downloader Redesign

**Date:** 2026-07-01
**Spec:** docs/specs/2026-07-01-youtube-downloader-redesign-design.md
**Plan:** docs/plans/2026-07-01-youtube-downloader-redesign.md
**Verify report:** docs/verifications/2026-07-01-youtube-downloader-redesign-verify.md (verdict: ready)
**Commits under review:** 4077833..81739bd on vibe/youtube-downloader-redesign

## Diff summary

- Files changed: 23 (code + tests + docs; plus plan/uv.lock bookkeeping)
- Lines added: 698, removed: 3810 (net −3112)
- Implementer commits: 9 (one per task) + per-task plan-completion bookkeeping commits
- Largest new construct: `app/tools/media_downloader.py` (+147 lines of orchestration)

## Findings

### Block
- None.

### Warn
- None that violate the spec. (The three risks below are pre-existing behaviors carried over unchanged, not regressions, and outside this refactor's scope.)

### Nit
- ~~`app/tools/media_downloader.py` — the `str(Path(f))`-keyed `conversion_map` in `_finalize_playlist` relies on the downloaded path string equalling its `Path` round-trip.~~ **RESOLVED** in commit `ca5acc6`: the map is now keyed on the original download path (`to_convert[i]`), removing the round-trip dependency.

## Post-review fixes (commit ca5acc6)

Applied at the user's "fix nits" request:
- **Playlist title sanitization** — new `sanitize_subfolder()` strips path separators (`/`, `\`) and falls back to `playlist` when nothing meaningful survives, so a title like `Rock/Pop` yields a single safe folder segment (`Rock_Pop`) rather than a nested/traversing path. Addresses self-critique risk #2. Tests: `test_sanitize_subfolder`, `test_download_playlist_unsafe_title`.
- **Robust conversion mapping** — playlist `conversion_map` keyed on the original download path. Addresses self-critique risk #3.
- Suite now 41 passing (was 39; +2 tests). Self-critique risk #1 (resolution unavailable) intentionally left as-is — it already fails gracefully and a fallback would be a behavior change beyond a nit.

## Pass-by-pass

- **Pass 1 (spec coverage):** All 9 Goals + Non-goals + Constraint C2 verified satisfied by verify-gate (3-pass unanimous). No Non-goal violated: no local-file conversion, no image/subtitle tables, no config file, no non-YouTube path. No block.
- **Pass 2 (plan fidelity):** Every plan task's Files appear in the diff; commit subjects match the plan's specified messages; commit order follows task order (Task 1→9). No block.
- **Pass 3 (code quality):** No duplicated logic across changed files; no new export lacks a caller/test (helpers `_finalize_single`, `_failed`, `_download_single/_playlist`, `calculate_success_stats`, `print_summary` all used; classifiers `is_audio_format`/`is_video_format` used by orchestration + parser choices). Public identifiers match the spec's wording (`--resolution`, `--format`, `--output-dir`). No block.
- **Pass 4 (simplicity):** Net −3112 lines; the change is dominated by deletion. `media_downloader.py` at 147 new lines is split into small single-purpose pure functions — not halvable without losing testability. `net: 0 lines cuttable — Lean already.`
- **Pass 5 (surgical-diff):** Independent auditor returned `clean`, 0 orphans; every hunk traces to a plan task and matches prescribed code verbatim. No block.
- **Pass 6 (self-critique):** three risks below.

## Self-critique (three risks the tests would not catch)

1. **Requested resolution unavailable.** All download tests mock pytubefix. If `--resolution 1440` is passed and `get_by_resolution("1440p")` returns `None`, `download_stream(None)` would raise; `download()`'s `try/except Exception` catches it and exits with an error message (no traceback dump). — Mitigation: graceful failure via the existing outer try/except. Pre-existing behavior (old code was identical). Follow-up if desired: fall back to highest resolution with a warning; add an integration test with a real short video.
2. **Playlist title with filesystem-unsafe characters.** `resolve_playlist_output` uses `playlist.title` directly as a subfolder name; a title containing `/` would create nested dirs. Not exercised by tests (fixture title is `MyList`). — Mitigation: none new. Pre-existing (the old playlist code also used the raw title). Follow-up if desired: sanitize the title before joining.
3. **Conversion-result mapping in playlists.** `_finalize_playlist` maps conversion results back to downloads by path-string equality. If a returned path string differs from its `Path` round-trip, an item could be reported unconverted despite success. — Mitigation: pattern preserved verbatim from working pre-existing code; low risk for normal paths. Follow-up if desired: key the map on a normalized `os.path.realpath`.

All three are inherited from the prior implementation and lie outside the spec's stated Goals/Non-goals; none are regressions introduced by this work.

## Diff

Full diff (verbatim) is available via:

```
git -C .vibe-worktrees/2026-07-01-youtube-downloader-redesign diff 4077833..81739bd
```

Per-file line counts (added/removed):

```
 41 322  README.md
  1   2  app/__init__.py
  0  56  app/tools/media_converter.py
147 392  app/tools/media_downloader.py
  0  24  app/tools/youtube_downloader.py
 24  87  app/utils/command_manager.py
  0 259  app/utils/config.py            (deleted)
  6   0  app/utils/constants.py         (new)
 11  29  app/utils/media_format.py
 32 403  doc/commands.md
  0 528  doc/configuration.md           (deleted)
  4  14  main.py
  0   4  pyproject.toml
  0   1  requirements.txt
 50 141  tests/test_command_manager.py
 11 277  tests/test_integration.py
 64 194  tests/test_media_converter.py
213 319  tests/test_media_downloader.py
 48 197  tests/test_media_format.py
  0 411  tests/test_playlist_downloader.py (deleted)
```

## Sign-off

- [ ] User reviewed findings.
- [ ] User reviewed diff.
- [ ] User approves proceeding to finish-branch.
