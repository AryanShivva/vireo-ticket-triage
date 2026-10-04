# How do I know the categories are right, and how often are they not?

**There is no ground truth in the pack.** The closing notes are written by agents, but they are messy and some say only "done". So I did not treat any
automatic agreement number as accuracy. What I did:

| Check | n | Result | Role |
|---|---|---|---|
| Audit 1: random tickets, I read message + note and judged the label | 80 (60 note-labelled, 20 model-labelled) | **6 wrong (7.5%)**, 4 of them would change the owning team | Used to *debug*. All 6 were rule bugs ("low mic pickup" read as a return pickup, "crackling" read as a cracked unit, typo'd "refund", vague note overriding a clear message). Fixed. |
| Audit 2: fresh random tickets (ids in `audit2_ticket_ids.csv`) | 100 (70/30) | **1 clear error, 1 ambiguous** ("update failed and won't turn on") | Holdout for that version. Wilson 95% interval for 1/100: 0.2%-5.4%. |
| Re-check after the last two changes | 4 changed rows in the audits | 3 corrected, 1 newly wrong ("speaker dead, no power" -> audio). Rule added. | Regression check |
| Audit 3: the 40 lowest-confidence model predictions | 40 of 2,330 model-labelled | **1 clear error** ("speaker won't turn on" -> app/firmware), 1 ambiguous | Where it is weakest |
| Model vs explicit notes, 5-fold out-of-fold | 9,600+ | 99.9% agreement | **Circular**: both sides come from the same rules. Shows the text model reproduces the rules, not that either is right. |
| Unit tests | 2 | pass | Guards the specific bugs found (timezone, 'twice', OTP, mic pickup, typo'd refund, blank CSAT/transfers) |

**Best estimate: about 1-3% of tickets get the wrong issue label, and a bit less get the wrong owning team.** Audit 2's 1% is a point estimate on 100
tickets, so treat the uncertainty as real. The bot's original tag, by the same standard, matches the real category only 70.7% of the time (and "Other" is never right).

**What it gets wrong:** (1) hardware that "won't turn on" after an update (hardware vs firmware is a genuine judgement call); (2) messages that mention both a
payment and a missing parcel ("amount deducted and nothing at my door"; the agent's note decides, the message alone is ambiguous); (3) very short messages
("sorted", "done") where only the model's guess exists; (4) anything outside the 18 types.

**Weaknesses of this validation:** the auditor is an AI model that also helped write the rules, so shared blind spots are likely; the right next step is 100 tickets
labelled by someone in Neha's team. I did not re-audit a fresh sample after the final rule fixes.

**Bug I found late:** the refund regex had doubled backslashes from a scripted patch, so typo'd refund notes were missed. It cost 2 points of note-rule coverage and
changed no final labels (the text model had been covering those rows). The unit test that caught it is in `tests/`.
