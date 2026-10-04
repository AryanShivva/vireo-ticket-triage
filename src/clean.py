"""Load + clean the Vireo exports. Every fix is logged in the returned `log` list."""
import pandas as pd, numpy as np

IST_OFFSET = pd.Timedelta(hours=5, minutes=30)

def load_clean(tickets_csv, orders_csv=None, products_csv=None):
    log = []
    t = pd.read_csv(tickets_csv)
    for c in ['created_at', 'first_response_at', 'resolved_at']:
        t[c] = pd.to_datetime(t[c])
    n0 = len(t)
    # 1. exact duplicate guard (policy s9: legacy re-imports may appear under both systems)
    key = ['customer_id', 'product_sku', 'customer_message', 'channel']
    dups = t.duplicated(key, keep=False)
    # only treat as dup if same customer/message within 3 days (generic phrases from different people are not dups)
    t = t.sort_values('created_at')
    grp = t.groupby(key)['created_at']
    gap = grp.diff().dt.days
    dupmask = gap.notna() & (gap <= 3)
    log.append(f'duplicate re-imports removed: {int(dupmask.sum())} (same customer+sku+channel+message within 3 days)')
    t = t[~dupmask].copy()
    # 2. legacy resolved_at is UTC (policy s9); everything else is IST
    leg = t.source_system == 'legacy_fd'
    t.loc[leg, 'resolved_at'] = t.loc[leg, 'resolved_at'] + IST_OFFSET
    log.append(f'legacy resolved_at shifted +5:30 (UTC->IST) on {int(leg.sum())} rows')
    # 3. window
    t['month'] = t.created_at.dt.to_period('M')
    t['in_window'] = t.created_at >= '2025-01-01'
    log.append(f'rows before 2025-01-01 (outside agreed window, kept but excluded from charts): {int((~t.in_window).sum())}')
    # 4. handle-time & SLA fields
    t['resp_min'] = (t.first_response_at - t.created_at).dt.total_seconds() / 60
    t['res_hours'] = (t.resolved_at - t.created_at).dt.total_seconds() / 3600
    t['handle_hours'] = (t.resolved_at - t.first_response_at).dt.total_seconds() / 3600
    bad = (t.handle_hours < 0)
    log.append(f'rows with resolution before first response after TZ fix: {int(bad.sum())} (set handle_hours=NaN)')
    t.loc[bad, ['handle_hours', 'res_hours']] = np.nan
    target = {'chat': 15, 'voice': 120, 'social': 240, 'email': 480}
    t['sla_target_min'] = t.channel.map(target)
    t['breach'] = t.resp_min > t.sla_target_min
    # 5. transfers: blank != 0
    t['transfers_known'] = t.transfers.notna()
    # 6. csat blank stays NaN (never 0)
    t['attended'] = t.status.isin(['resolved', 'closed'])
    # 7. refund: flag legacy native-unit issue (checked in analysis, see out/refund_unit_check.txt)
    t['has_refund'] = t.refund_amount_inr.notna()
    t['has_repl'] = t.replacement_issued.eq('Y')
    return t.sort_values('ticket_id').reset_index(drop=True), log
