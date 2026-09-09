# Eng session 2026-09-09-whatif-three-views

- Created: 2026-09-08T22:01:28Z
- Work type: W4
- Goal: Typed what-if views: paper, holdings-as-of-D, and path are three records; one holdings URL; compare_path starts at fork.

## Log

- 2026-09-08T22:01:28Z scaffolded
- Plan written from post-ship SDR (mixed → reshape): three typed views; one holdings URL; cash as of D on holdings; GET /{id} is the document; drop compare_path since. Not implemented.
- Implemented: `PaperView` / `HoldingsView` / `PathView`; `editor_page` adds `cash_today`; `GET /{id}` is the document; `compare_path` has no `since`. Tests 55 what-if + `eng_verify` PASS 935. Browser: header cash stays today after date change; holdings cash on 2026-07-02 differs; document JSON has no held/path.
- Feature list flipped: `typed-views` and `path-at-fork` `passes: true` after `pytest apps/analysis_web/tests/test_histories.py apps/analysis_web/tests/test_alt_history.py -q` (39 passed).
- Follow-on reshape (plan_paper_book.md): PaperView is the book; EditorPage is the page; holdings_on does not call paper_on; one held-table partial. Scaffold of `2026-09-09-whatif-paper-book` blocked (eng/sessions not writable).
- Implemented that reshape. What-if pytest 55; analysis_web 327; `eng_verify` PASS 934 (Windows Python, PYTHONUTF8=1). Live: HTML first paint close/value are —; fragment fills marks; GET /{id} has no held/path; holdings cash 2026-07-02 ≠ today; no live_nav.js.
- Follow-on reshape (plan_asof_d.md): stamp `BookState.as_of` to D after replay; PaperView has no History; sold-later is a page set; holdings card shows cash on D. Overlay 0-fill left disputed. Scaffold of a new session blocked.
- Implemented as-of-D reshape. What-if pytest 55; `eng_verify` PASS 934 (Windows Python, PYTHONUTF8=1).
