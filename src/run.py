"""Vireo ticket re-categoriser. One command:  python src/run.py --data-dir <folder with the 6 csv exports> --out out
Outputs: labelled_tickets.csv, monthly_by_category.csv, monthly_by_team.csv, charts/*.png, metrics.json, cleaning_log.txt"""
import argparse, glob, json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import clean, categorise

CONTACT_COST = {'chat': 210, 'email': 260, 'voice': 520, 'social': 240}   # policy s4
TRANSFER_COST, BREACH_CREDIT, BLENDED = 305, 350, 290
FL = {'chat': 'Chat Frontline', 'email': 'Email Frontline', 'voice': 'Voice Frontline', 'social': 'Chat Frontline'}  # social is worked by Chat (policy s2)

def find(d, name):
    m = [f for f in glob.glob(os.path.join(d, '*')) if os.path.basename(f).lower().endswith(name)]
    if not m: sys.exit(f'missing {name} in {d}')
    return m[0]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--data-dir', required=True); ap.add_argument('--out', default='out')
    a = ap.parse_args(); os.makedirs(os.path.join(a.out, 'charts'), exist_ok=True)
    t, log = clean.load_clean(find(a.data_dir, 'tickets.csv'))
    ag = pd.read_csv(find(a.data_dir, 'agents.csv'))
    c, clf, _ = categorise.categorise(t)
    c['true_team'] = np.where(c.true_owner == 'Frontline', c.channel.map(FL), c.true_owner)
    c['routed_ok'] = np.where(c.true_owner == 'Frontline', c.assigned_team.str.endswith('Frontline'), c.assigned_team == c.true_owner)
    c = c.merge(ag[['agent_id', 'team']].rename(columns={'team': 'resolver_team'}), on='agent_id', how='left')
    # repeat contact (policy s10): same customer, same issue, within 30 days of previous resolution
    c = c.sort_values(['customer_id', 'issue', 'created_at'])
    c['repeat'] = (c.created_at - c.groupby(['customer_id', 'issue']).resolved_at.shift()).dt.days.between(0, 30)
    c = c.sort_values('ticket_id').reset_index(drop=True)
    w = c[c.in_window].copy(); M = {}
    M['rows_total'] = len(c); M['rows_in_window'] = len(w)
    # --- categoriser quality (vs explicit closing notes, out-of-fold) ---
    lab = c.note_issue.notna()
    M['note_label_coverage'] = round(lab.mean(), 4)
    M['model_oof_agreement_with_notes'] = round((c.model_issue[lab] == c.note_issue[lab]).mean(), 4)
    M['tag_matches_true_category'] = round((w.category == w.true_category).mean(), 4)
    M['other_tag_rows'] = int((w.category == 'Other').sum())
    # --- volume: tag vs true ---
    tag = w.assigned_team.value_counts(normalize=True); tru = w.true_team.value_counts(normalize=True)
    M['share_by_tag_team'] = (tag * 100).round(1).to_dict(); M['share_by_true_team'] = (tru * 100).round(1).to_dict()
    b = w[w.assigned_team == 'Billing']
    M['billing_tagged'] = len(b); M['billing_tagged_not_billing'] = int((~b.routed_ok).sum())
    M['billing_misroute_share'] = round((~b.routed_ok).mean(), 4)
    M['billing_misroute_mix'] = b[~b.routed_ok].true_owner.value_counts().to_dict()
    # --- cost of one misrouted Billing ticket ---
    bm, bg = b[~b.routed_ok], b[b.routed_ok]
    hd = b[b.transfers_known]
    x_m, x_g = hd[~hd.routed_ok].transfers.mean(), hd[hd.routed_ok].transfers.mean()
    br_m, br_g = bm.breach.mean(), bg.breach.mean()
    rp_m, rp_g = bm.repeat.mean(), bg.repeat.mean()
    cc = bm.channel.map(CONTACT_COST).mean()
    per = {'extra_transfers': (x_m - x_g) * TRANSFER_COST, 'extra_breach_credit': (br_m - br_g) * BREACH_CREDIT, 'extra_repeat_contact': (rp_m - rp_g) * cc}
    M['misroute_rates'] = {'transfers': [round(x_m, 3), round(x_g, 3)], 'breach': [round(br_m, 3), round(br_g, 3)], 'repeat': [round(rp_m, 3), round(rp_g, 3)],
                           'csat': [round(bm.csat_score.mean(), 2), round(bg.csat_score.mean(), 2)],
                           'median_resolution_h': [round(bm.res_hours.median(), 1), round(bg.res_hours.median(), 1)]}
    M['cost_per_misrouted_ticket_inr'] = {k: round(v) for k, v in per.items()}; cpt = sum(per.values()); M['cost_per_misrouted_ticket_inr']['total'] = round(cpt)
    h26 = w[w.created_at >= '2026-01-01']; q = (pd.Timestamp('2026-07-01') - pd.Timestamp('2026-01-01')).days / 91.25
    bq = h26[h26.assigned_team == 'Billing']
    M['h1_2026_billing_tagged_per_quarter'] = round(len(bq) / q); M['h1_2026_billing_misrouted_per_quarter'] = round((~bq.routed_ok).sum() / q)
    now = (~bq.routed_ok).sum() / q; tgt = 0.10 * len(bq) / q
    M['target_misroute_share'] = 0.10; M['avoided_misroutes_per_quarter'] = round(now - tgt)
    M['saving_per_quarter_inr_on_export'] = round((now - tgt) * cpt)
    M['export_tickets_per_week_h1_2026'] = round(len(h26) / (181 / 7), 1)
    M['scale_factor_to_650_per_week'] = round(650 / M['export_tickets_per_week_h1_2026'], 2)
    M['saving_per_quarter_inr_at_650_per_week'] = round(M['saving_per_quarter_inr_on_export'] * M['scale_factor_to_650_per_week'])
    # --- load per agent (resolver team), H1 2026 ---
    wk = 181 / 7; n_ag = ag.groupby('team').size()
    tab = pd.DataFrame({'agents': n_ag, 'resolved_per_agent_week': h26.groupby('resolver_team').size() / n_ag / wk,
                        'true_owned_per_agent_week': h26.groupby('true_team').size() / n_ag / wk}).round(2)
    M['load_per_agent_week_h1_2026'] = tab.to_dict('index')
    M['billing_tickets_resolved_by_logistics_agents'] = int(((c.assigned_team == 'Billing') & (c.resolver_team == 'Logistics')).sum())
    # --- other checks ---
    M['sla_breach_rate_all'] = round(w.breach.mean(), 4); M['sla_credits_inr_all_window'] = int(w.breach.sum() * BREACH_CREDIT)
    M['refund_and_replacement_same_ticket'] = int((w.has_refund & w.has_repl).sum())
    M['refund_and_replacement_value_inr'] = int(w[w.has_refund & w.has_repl].refund_amount_inr.sum())
    M['handle_hours_median_by_assigned_team'] = w.groupby('assigned_team').res_hours.median().round(1).to_dict()
    json.dump(M, open(os.path.join(a.out, 'metrics.json'), 'w'), indent=2, default=str)
    open(os.path.join(a.out, 'cleaning_log.txt'), 'w').write('\n'.join(log) + '\n')
    # --- tables ---
    keep = ['ticket_id', 'created_at', 'channel', 'category', 'assigned_team', 'issue', 'true_category', 'true_team', 'label_source', 'model_conf', 'routed_ok', 'agent_id', 'resolver_team', 'transfers', 'breach', 'csat_score']
    c[keep].to_csv(os.path.join(a.out, 'labelled_tickets.csv'), index=False)
    w['m'] = w.month.astype(str)
    w.groupby(['m', 'true_category']).size().unstack(fill_value=0).to_csv(os.path.join(a.out, 'monthly_by_category.csv'))
    w.groupby(['m', 'category']).size().unstack(fill_value=0).to_csv(os.path.join(a.out, 'monthly_by_category_bot_tag.csv'))
    w.groupby(['m', 'assigned_team']).size().unstack(fill_value=0).to_csv(os.path.join(a.out, 'monthly_by_team_as_routed.csv'))
    w.groupby(['m', 'true_team']).size().unstack(fill_value=0).to_csv(os.path.join(a.out, 'monthly_by_team_true.csv'))
    charts(w, a.out); print(json.dumps(M, indent=1, default=str)[:3500])

def charts(w, out):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    def stack(df, title, fn, cmap='tab20'):
        fig, ax = plt.subplots(figsize=(11, 5.2)); df.plot(kind='bar', stacked=True, ax=ax, colormap=cmap, width=.85)
        ax.set_title(title, loc='left', fontsize=12, fontweight='bold'); ax.set_xlabel(''); ax.set_ylabel('tickets / month')
        ax.legend(fontsize=7.5, ncol=2, frameon=False, bbox_to_anchor=(1.01, 1), loc='upper left'); ax.spines[['top', 'right']].set_visible(False)
        plt.xticks(rotation=45, ha='right'); plt.tight_layout(); fig.savefig(os.path.join(out, 'charts', fn), dpi=140); plt.close(fig)
    stack(w.groupby(['m', 'true_category']).size().unstack(fill_value=0), 'Monthly tickets by re-categorised issue (text-based), Jan 2025 - Jun 2026', 'monthly_by_category_recategorised.png')
    stack(w.groupby(['m', 'category']).size().unstack(fill_value=0), "Monthly tickets by the bot's original tag (for comparison)", 'monthly_by_category_bot_tag.png')
    stack(w.groupby(['m', 'assigned_team']).size().unstack(fill_value=0), 'Monthly tickets by team the ticket was ROUTED to', 'monthly_by_team_as_routed.png', 'tab10')
    stack(w.groupby(['m', 'true_team']).size().unstack(fill_value=0), 'Monthly tickets by team that OWNS the work (re-categorised)', 'monthly_by_team_true.png', 'tab10')
    teams = ['Logistics', 'Chat Frontline', 'Billing', 'Email Frontline', 'Returns Desk', 'Voice Frontline', 'Escalations & Warranty']
    r = w.assigned_team.value_counts(normalize=True).reindex(teams) * 100; o = w.true_team.value_counts(normalize=True).reindex(teams) * 100
    fig, ax = plt.subplots(figsize=(10, 4.8)); x = np.arange(len(teams))
    ax.bar(x - .2, r, .4, label='as routed by bot tag', color='#b0b7c3'); ax.bar(x + .2, o, .4, label='who actually owns the work', color='#1f6feb')
    for i in range(len(teams)): ax.text(x[i] - .2, r.iloc[i] + .4, f'{r.iloc[i]:.0f}%', ha='center', fontsize=8); ax.text(x[i] + .2, o.iloc[i] + .4, f'{o.iloc[i]:.0f}%', ha='center', fontsize=8, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels([t.replace(' ', '\n', 1) for t in teams], fontsize=8); ax.set_ylabel('% of tickets'); ax.legend(frameon=False)
    ax.set_title('Share of ticket volume: routed vs real owner (Jan 2025 - Jun 2026)', loc='left', fontweight='bold'); ax.spines[['top', 'right']].set_visible(False)
    plt.tight_layout(); fig.savefig(os.path.join(out, 'charts', 'routed_vs_true_share.png'), dpi=140); plt.close(fig)

if __name__ == '__main__': main()
