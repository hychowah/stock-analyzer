# Eng session 2026-09-09-whatif-three-views

- Created: 2026-09-08T22:01:28Z
- Work type: W4
- Goal: Typed what-if views: paper, holdings-as-of-D, and path are three records; one holdings URL; compare_path starts at fork.

## Log

- 2026-09-08T22:01:28Z scaffolded
- Plan written from post-ship SDR (mixed → reshape): three typed views; one holdings URL; cash as of D on holdings; GET /{id} is the document; drop compare_path since. Not implemented.
- Implemented: `PaperView` / `HoldingsView` / `PathView`; `editor_page` adds `cash_today`; `GET /{id}` is the document; `compare_path` has no `since`. Tests 55 what-if + `eng_verify` PASS 935. Browser: header cash stays today after date change; holdings cash on 2026-07-02 differs; document JSON has no held/path.
- Feature list flipped: `typed-views` and `path-at-fork` `passes: true` after `pytest apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_alt_history.py -q` (39 passed).
