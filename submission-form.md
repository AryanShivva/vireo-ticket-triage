# Submission form - Vireo Audio, Support Tickets (Set E)


**1. What did you build, and what business outcome does it move? State the number and the money.**
A command-line tool that cleans the helpdesk exports, re-reads each ticket's text to assign the real issue (18 types) and the team that owns it, and produces
the monthly volume charts by category and by team (as tagged and as re-read), plus the cost of mis-routing.
Outcome: **cut the share of Billing-queue tickets that are really Logistics/Returns work from 43.7% (1,060 of 2,425) to 10%** within a quarter of fixing the bot's routing.
That is ~142 fewer wrong-queue tickets a quarter, **about Rs 45,000 a quarter** on the export's volume (181 tickets/week) at Rs 317 per mis-routed ticket
(Rs 219 extra transfers + Rs 87 extra SLA credits + Rs 11 repeat contacts), or **about Rs 1.6 lakh a quarter** if volume is the 650/week quoted. It also changes the hiring decision:
Logistics is the biggest real queue (28.8% vs 16.4% tagged), Billing is 18.2% vs 20.8% tagged. Honest framing: the saving alone does not repay two hires (Rs 9 lakh/yr); the point is not hiring on wrong numbers.

**2. What does one run cost, and what would a month cost at ~650 tickets a week?**
Rs 0. No paid API calls: rules + a scikit-learn model that trains on the data in the run. ~28 seconds on a laptop for 11,780 tickets, ~1 minute at 3x that.
Arithmetic: 650 tickets/week x 52 / 12 = ~2,817 tickets a month; 2,817 x Rs 0 per ticket = Rs 0 (compute only). If someone later replaces the model with an LLM call per ticket,
that cost is new and I have not measured it; it would scale linearly with those 2,817 tickets.

**3. How do you know it works? Sample size, how you checked, error rate, kind of case it gets wrong.**
No ground truth exists in the pack, so I hand-audited (I read message + note and judged the label): 80 tickets (6 wrong = 7.5%, all rule bugs, fixed), then a fresh 100 (1 clear error, 1 ambiguous; Wilson 95% interval 0.2-5.4%),
then the 40 lowest-confidence model predictions (1 clear error). ~220 tickets in total. Best estimate: 1-3% wrong issue label, slightly less wrong owning team. The bot's own tag matches the real category 70.7% of the time.
Weak spots: "won't turn on after update" (hardware vs firmware), messages that mix a payment and a missing parcel, one-word messages. The 99.9% model-vs-notes agreement is circular and is not an accuracy claim. Details: `validation/VALIDATION.md`.

**4. Did you change, narrow, or push back on the client's ask? [can only raise your score]**
Yes. (a) Priya asked for charts of the bot's tags and "most volume gets the hires". I charted both tagged and re-read, because the answer flips: Billing's 22% includes 941 delivery tickets and 115 Returns tickets. Recommended holding the two Billing hires for a quarter and fixing routing (Arjun asked for a process fix if possible).
(b) I did not use volume as the hiring test: volume is not capacity, and Tier 2 is not comparable on volume (policy s6). (c) Neha's "Logistics is drowning" is partly right (9.7 tickets per agent-week vs Billing 7.9; Logistics agents resolved 795 Billing-tagged tickets) but her evidence (long resolution times) is mostly courier waiting, and the hand-offs go Billing -> Logistics, not "from everyone". (d) Narrowed: no per-agent performance ranking (breaches are charged to the resolving agent, which is unfair on misrouted tickets).

**5. What is wrong with what you are handing us? [can only raise your score]**
- The audit ground truth is my own reading, and I helped write the rules, so shared blind spots are likely. Needs 100 tickets labelled by a human at Vireo.
- I did not re-audit a fresh sample after the last rule fixes.
- Team ownership of cancellation / address change / coupon is my assumption (the Billing headline is robust to it: 941 of 1,060 are plain "not delivered").
- The export averages 181 tickets/week, not ~650. I do not know whether it is a sample; the rupee figures scale, the percentages should not, but I have not verified.
- Rs 317 per mis-routed ticket uses helpdesk-era transfers only, and treats extra breaches as caused by mis-routing (correlation, not proof); no staffing-hours model.
- A refund regex bug (doubled backslashes) went unnoticed until a unit test caught it; it changed no final labels, but it shows the rules are hand-written and fragile.
- `run.py` has no unit tests of its own beyond a full run; charts are plain matplotlib; no UI.

**6. What did you deliberately leave out, and why that rather than something else?**
An LLM labeller (no ground truth to tune it, a cost per ticket, and rules on the agents' own notes were more consistent and free); per-agent performance and CSAT drivers (policy says Tier 2 and misrouted tickets distort them);
product/lot-code defect analysis using orders.csv (a likely separate finding, but it does not bear on the hiring decision); a dashboard UI. Cross-system duplicate removal was built, found zero duplicates, and is left in as a guard.

**7. Anything you built or found that nobody asked for?**
Legacy `resolved_at` is UTC: without correcting it 2,379 tickets resolve before creation. 29.3% of the bot's tags are wrong at category level ("Other" is 14% of tickets and 70% of it is billing/delivery work). SLA credits cost Rs 4.5 lakh in the window (Rs 350 each). Only 2 tickets got both a refund and a replacement (Rs 7,249), so that is not worth chasing. No refund-unit problem exists in the legacy data (refund/order-value ratios match across systems).

**8. What did you use AI for?** 
Claude (Anthropic) throughout: reading the data, writing the pipeline and tests, running audits, and drafting the memo. It helped most on fast exploration and on spotting the Billing/Logistics pattern; it wasted time on whole-note regexes (58% agreement) and on a message-override rule that made one case worse; a scripted patch introduced the refund-regex bug. Discarded: LLM-labelling idea, duplicate detector (kept as guard), refund-unit rescale, message override.
Cost: Rs 0 (Claude Free plan; no API/paid usage). Screen recording: https://drive.google.com/file/d/1EBY2366ZFfPFyCjfhfkSozYbMPAANU-a/view?usp=sharing

**9. Your Public Google Drive Link** https://drive.google.com/drive/folders/1xvyvggpCYr1UAgLspNH_7pYDN3ykruuy?usp=sharing

**10. Someone picks this up on Monday and you are unreachable. The three things they need to know.**
1. Billing's 22% is mostly an intake-bot routing problem (44% of its queue is Logistics/Returns work); the first action is Sameer's bot rule change, then re-run `python src/run.py` after 30 days to see if the share drops from 44% to 10%.
2. Confirm the volume: the export is 181 tickets/week, the client says ~650. All rupee figures scale with that.
3. Get 100 tickets hand-labelled at Vireo to replace my audit before anyone quotes the error rate; the ownership map is in `src/taxonomy.py`.

**11. Honest hours spent:** 6 hours

**12. Github Repo Link** : https://github.com/AryanShivva/vireo-ticket-triage.git
