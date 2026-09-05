# Eng session 2026-09-05-law-graph-catalog-pin

- Created: 2026-09-05T09:09:19Z
- Work type: W1
- Goal: C1 live law + C5 thin Pin + C2 phase graph (2.38.0) + C3 catalog RunQuery + C4 UI query

## Log

- 2026-09-05T09:09:19Z scaffolded
- C1: live law 2.36-only + one orch sequence; VERSION 2.37.0
- Design review of remaining C2–C5: mixed / reshape. Absorbed: C5 entire before C2 so `pins/2.38.0` publishes thin once; C2 edges (not PHASE_ORDER walk) are the gate; C3 stamps quote_listing at rebuild; C4 returns RunQuery (delete audit alias). Did not split C5 — that would be a time split of one Pin module. Plan: `eng/sessions/2026-09-05-law-graph-catalog-pin/plan.md`. Next: C5.
- C5: Pin COPY_REL is Mode A only; resolve requires PIN.json; both live and published scaffold run scripts/scaffold_session.py; identity live=provenance, published=VERSION+PIN.json; deleted force=. Next: C2.
- C2: PhaseNode DAG is the gate; derived tables; VERSION 2.38.0; published thin pins/2.38.0. Next: C3.
