# Eng session 2026-09-10-history-listing-series

- Created: 2026-09-10T09:34:28Z
- Work type: W2
- Goal: Daily closes are one in-process series per listing; Yahoo period is fetch metadata, not store identity

## Log

- 2026-09-10T09:34:28Z scaffolded
- Reshape: daily closes are one in-process series per listing. `HistoryService.get_many(..., since=)` is the only read. Yahoo period tokens live in `period_covering` / `YahooHistoryBackend`. HTTP `?range=` is a display slice. MTM Play and what-if pass the start date. QuoteService and process RAM unchanged. Deleted `range_for_span`. Coverage is the fetched period watermark (not `bars[0].t`). An expired long series is refetched at that period so a short poll cannot shrink it. `eng_verify` PASS (implementer did not flip `passes`).
