"""Re-categorise tickets from free text.
Stage 1 (labels): closing-note issue phrase -> rules (high precision, ~92% coverage).
Stage 2 (model): TF-IDF (word+char) logistic regression on the CUSTOMER MESSAGE ONLY, trained on stage-1 labels,
                 so it works at intake (before an agent has written a note) and fills rows stage 1 can't label.
final_issue = stage1 if present else stage2. `label_source` records which."""
import numpy as np, pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict, StratifiedKFold
from taxonomy import note_label, rule_label, combined_label, ISSUES

def _norm(s): return s.fillna('').str.lower().str.replace(r'\\n|\n', ' ', regex=True)
def _vec():
    return (TfidfVectorizer(ngram_range=(1,2), min_df=2, sublinear_tf=True),
            TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=3, sublinear_tf=True))

def categorise(t, seed=7):
    t = t.copy()
    msg = _norm(t.customer_message)
    t['note_issue'] = [combined_label(n, m) for n, m in zip(t.agent_notes, t.customer_message)]
    t['msg_rule_issue'] = t.customer_message.map(rule_label)
    lab = t.note_issue.notna()
    v1, v2 = _vec()
    X = hstack([v1.fit_transform(msg), v2.fit_transform(msg)]).tocsr()
    clf = LogisticRegression(max_iter=2000, C=8, class_weight='balanced')
    y = t.note_issue
    # out-of-fold predictions for labelled rows (honest accuracy), full-fit predictions for unlabelled rows
    skf = StratifiedKFold(5, shuffle=True, random_state=seed)
    oof = np.empty(len(t), dtype=object); conf = np.zeros(len(t))
    idx = np.where(lab)[0]
    pr = cross_val_predict(clf, X[idx], y.iloc[idx], cv=skf, method='predict_proba')
    classes = np.array(sorted(y.dropna().unique()))
    oof[idx] = classes[pr.argmax(1)]; conf[idx] = pr.max(1)
    clf.fit(X[idx], y.iloc[idx])
    un = np.where(~lab)[0]
    if len(un):
        pu = clf.predict_proba(X[un]); oof[un] = clf.classes_[pu.argmax(1)]; conf[un] = pu.max(1)
    t['model_issue'] = oof; t['model_conf'] = conf
    t['issue'] = np.where(lab, t.note_issue, t.model_issue)
    t['label_source'] = np.where(lab, 'note_rule', 'message_model')
    t['true_category'] = t.issue.map(lambda k: ISSUES[k][0])
    t['true_owner'] = t.issue.map(lambda k: ISSUES[k][1])
    return t, clf, (v1, v2)
