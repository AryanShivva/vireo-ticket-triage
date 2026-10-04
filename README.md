# Vireo Audio - support ticket re-categoriser (Set E)

Re-reads every ticket's free text, assigns the **real** issue category and the **team that owns the work**, then compares that with the
bot's tag. Produces the monthly charts by category and by team that Priya asked for, in two versions (as tagged / as re-read),
plus the cost of mis-routing.

**Headline:** 43.7% of tickets routed to Billing (1,060 / 2,425) are really Logistics or Returns work. Logistics is the largest team by real
volume (28.8%), Billing is 18.2%. See `MEMO.md` / `MEMO.pdf`.

## Run it (clean machine, Python 3.10+)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python tests/test_smoke.py                              # 2 tests, a few seconds, no client data
python src/run.py --data-dir /path/to/folder/with/csvs --out out
```
`--data-dir` needs the exports whose file names end in `tickets.csv` and `agents.csv` (prefixes such as `99ca...-tickets.csv` are fine).
No API key, no network, no paid calls. About 30 seconds for 11.8k tickets. Verified in a fresh virtualenv; output is deterministic (fixed seeds).

Outputs in `out/` (a copy from my run is in `results/`): `charts/*.png`, `monthly_by_category.csv`, `monthly_by_category_bot_tag.csv`,
`monthly_by_team_as_routed.csv`, `monthly_by_team_true.csv`, `labelled_tickets.csv` (no message text), `metrics.json`, `cleaning_log.txt`.
Raw exports are NOT in this repo (customer data).

## How it works
1. `src/clean.py` - legacy `resolved_at` is UTC, so +5:30 to IST (policy s9; without it 2,379 tickets resolve *before* they were created). Blank `transfers`
   on legacy rows stays blank, blank CSAT stays blank, SLA breach per policy s3 targets. Duplicate re-imports are checked for (none found).
2. `src/taxonomy.py` - 18 issue types -> category -> owning team. Ordered regex rules, applied to the *issue phrase* in the agent's closing note.
3. `src/categorise.py` - rows whose note is vague ("done", "see prev", 18%) get a TF-IDF (word + character n-gram) logistic regression trained on the
   message text of the explicit-note rows. Character n-grams matter: messages are full of typos and Hinglish.
4. `src/run.py` - volume tables, charts, per-ticket cost of mis-routing, per-agent load (using the resolving agent's team, since `agent_id` is who actually did the work).

## Decisions I made where the brief was silent
- **Window:** the README says Jan 2025-Jun 2026 but 139 legacy tickets are from Jun-Dec 2024. Kept in the data, excluded from charts and headline numbers.
- **Who owns what:** cancellation / coupon / invoice / payment -> Billing; address change, wrong item, transit damage, not delivered -> Logistics; refund status and
  return pickup -> Returns Desk; warranty/RMA and dead hardware -> Escalations & Warranty; everything else -> the channel's Frontline team (social -> Chat, policy s2).
  Billing's headline result is insensitive to this: 941 of the 1,060 mis-routed tickets are plain "not delivered".
- **"Biggest team" is not the hiring test.** Volume is not capacity; Tier 2 is excluded from volume comparisons (policy s6).
- **Cost per mis-routed ticket (Rs 317)** = extra transfers x Rs 305 + extra breach rate x Rs 350 + extra repeat-contact rate x channel cost (policy s3-s4), comparing
  mis-routed vs correctly-routed Billing tickets. Transfers exist only in the helpdesk era, so that component uses post-14-Sep-2025 rows only.
- **Volume mismatch:** the form quotes ~650 tickets/week; this export averages 181/week (Jan-Jun 2026). I report both and did not guess which is right.

## Known problems (also in the submission form)
See `validation/VALIDATION.md`. Short version: ground truth for the audit was my own reading; the explicit-note labels are rule output, so the 99.9% model
agreement is circular and is NOT an accuracy figure; cancellation/address/coupon ownership is my assumption; no tests of `run.py` itself beyond the full run.

## Layout
`src/` code - `tests/` smoke tests - `results/` my run's outputs - `validation/` audit notes and the ticket ids I audited - `MEMO.md/.pdf` the memo - `submission-form.md`
