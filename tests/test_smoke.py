"""Run: python tests/test_smoke.py   (no pytest needed). Uses tiny synthetic frames, not client data."""
import os, sys, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pandas as pd
from taxonomy import rule_label, note_label, combined_label
import clean

def test_rules():
    assert rule_label('paid but package not delivered even after 11 days') == 'delivery_not_received'
    assert rule_label('charged twice for one order') == 'dup_or_failed_payment'
    assert rule_label('i have to charge it twice a day') == 'battery_charging'     # 'twice' must not mean billing
    assert rule_label('otp not coming on my number') == 'account_login'            # 'not rece..' must not mean delivery
    assert note_label('issue: low mic pickup | checked mic permissions') == 'audio_quality'   # not a return pickup
    assert note_label('1. Refudn pending 2. checked') == 'refund_status'          # typo tolerant
    assert combined_label('done', 'anything') is None                               # vague note -> model decides
    assert combined_label('rplc approved. issue: wrong variant rcvd', 'opened the parcel and it is a completely different thing') == 'wrong_item'

def test_clean():
    csv = ("ticket_id,created_at,first_response_at,resolved_at,status,channel,customer_id,order_id,product_sku,category,priority,assigned_team,agent_id,transfers,csat_score,refund_amount_inr,refund_reason_code,replacement_issued,customer_message,agent_notes,source_system\n"
           "T1,2025-03-01 10:00,2025-03-01 10:10,2025-03-01 07:00,resolved,chat,C1,,P,Other,Low,Chat Frontline,A1,,,,,N,hi,ok,legacy_fd\n"       # 07:00 UTC == 12:30 IST
           "T2,2026-03-01 10:00,2026-03-01 10:30,2026-03-01 12:00,resolved,chat,C2,,P,Other,Low,Chat Frontline,A1,0,,,,N,hi2,ok,helpdesk\n")
    p = '/tmp/_t.csv'; open(p, 'w').write(csv)
    t, log = clean.load_clean(p)
    r1 = t.set_index('ticket_id').loc['T1']
    assert str(r1.resolved_at) == '2025-03-01 12:30:00', r1.resolved_at          # UTC->IST applied to legacy only
    assert str(t.set_index('ticket_id').loc['T2'].resolved_at) == '2026-03-01 12:00:00'
    assert bool(r1.breach) is False and bool(t.set_index('ticket_id').loc['T2'].breach) is True  # 30 min > 15 min chat target
    assert t.csat_score.isna().all()                                              # blank CSAT never becomes 0
    assert not t.set_index('ticket_id').loc['T1'].transfers_known                 # legacy blank transfers != 0

if __name__ == '__main__':
    test_rules(); test_clean(); print('all tests passed')
