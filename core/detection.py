from dataclasses import dataclass, field
import re, unicodedata
import pandas as pd
from .recommend import recommend_for

THRESHOLD = 0.5
CONTENT_MIN_RATIO = 0.5   # fraction de valeurs devant matcher la regex pour "confirmer" la colonne

@dataclass
class ColumnRisk:
    column: str
    category: str
    confidence: float
    signals: list = field(default_factory=list)
    examples_masked: list = field(default_factory=list)
    recommendation: str = ""
    is_quasi_id: bool = False
    has_inline_pii: bool = False

def _norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()

# Profils par categorie : nommage (strong/weak), regex de contenu, plage d'unicite attendue, dtypes OK.
# unicity = (lo, hi) ; dtype = set de "kind" pandas (O=object, i/u=int, f=float, M=datetime, b=bool).
PROFILES = {
    "email": dict(
        strong=r"(e-?mail|courriel|\bmel\b)", weak=None,
        content=re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        uniq=(0.5, 1.01), dtypes={"O"}, atomic=True),
    "phone": dict(
        strong=r"(tel|phone|mobile|cell|fixe|ligne)", weak=None,
        content=re.compile(r"(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{2,3}\)?[\s.\-]?)?\d{2,4}[\s.\-]?\d{2,4}[\s.\-]?\d{2,4}"),
        uniq=(0.3, 1.01), dtypes={"O", "i", "u"}, atomic=True),
    "name": dict(
        strong=r"(^|_)(nom|prenom|surname|first_?name|last_?name|full_?name|family_?name)(_|$)", weak=None,
        content=None, uniq=(0.3, 1.01), dtypes={"O"}, atomic=True),
    "address": dict(
        strong=r"(adresse|address|\brue\b|street|avenue|\bav\b|\bbp\b|numero|num_?voie)", weak=None,
        content=None, uniq=(0.3, 1.01), dtypes={"O"}, atomic=True),
    "id": dict(
        strong=r"(ssn|\bsin\b|\bcin\b|passport|\bnir\b|num_?secu|securite_?sociale|license_?num)",
        weak=r"(^|_)(id|identifiant|uid|ref)(_|$)",
        content=re.compile(r"^\d{1,3}[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{3}$|^\d{3}-\d{2}-\d{4}$"),
        uniq=(0.7, 1.01), dtypes={"O", "i", "u"}, atomic=True),
    "health": dict(
        strong=r"(sante|health|medic|diagnos|patholog|traitement|allerg|\bicd\b|ordonnance|prescription)", weak=None,
        content=None, uniq=(0.0, 1.01), dtypes={"O"}, atomic=True),
    "quasi_id": dict(
        strong=r"(code_?postal|\bzip\b|\bcp\b|naissance|\bdob\b|birth|date_?nais|\bsexe\b|\bgenre\b|\bage\b|nationalite|ville|city|town|region|departement)", weak=None,
        content=re.compile(r"^\d{5}$"),  # confirme un code postal FR si present
        uniq=(0.0, 0.95), dtypes={"O", "i", "u", "f", "M"}, atomic=True),
}

def _mask(v, cat):
    s = str(v)
    if cat == "email" and "@" in s:
        u, d = s.split("@", 1)
        tld = d.split(".")[-1] if "." in d else "***"
        return f"{u[:1]}***@*.{tld}"
    if cat == "phone":
        d = re.sub(r"\D", "", s)
        return (d[:2] + "*" * max(len(d) - 5, 0) + d[-3:]) if len(d) >= 5 else "***"
    if cat in ("name", "address"):
        return s[:1] + "***"
    return "***"

def _unicity_ok(u, lo, hi):
    return lo <= u <= hi

def score_column(col, series, n_sample):
    signals = []
    scores = {}
    cn = _norm(col)
    vals_all = series.dropna()
    n_vals = len(vals_all)
    uniq = (vals_all.nunique() / n_vals) if n_vals else 0.0
    sample_limit = min(2000, max(n_sample, 1))
    sample = vals_all.astype(str)
    if len(sample) > sample_limit:
        sample = sample.sample(n=sample_limit, random_state=0)
    n_s = len(sample)
    dtype_kind = str(series.dtype.kind) if hasattr(series, "dtype") else "O"
    # "texte libre" = objet, valeurs longues en moyenne (plusieurs tokens)
    avg_tokens = (sample.str.split().str.len().mean() if n_s else 0) or 0
    is_freetext = (dtype_kind == "O") and (avg_tokens > 3)

    for cat, p in PROFILES.items():
        s = 0.0
        if p["strong"] and re.search(p["strong"], cn):
            s += 0.60; signals.append(f"name:{cat}(strong)")
        elif p["weak"] and re.search(p["weak"], cn):
            s += 0.25; signals.append(f"name:{cat}(weak)")
        if p["content"] is not None and n_s:
            hits = sum(1 for v in sample if p["content"].search(v))
            ratio = hits / n_s
            if ratio >= CONTENT_MIN_RATIO:
                s += 0.30 * min(ratio / 0.8, 1.0); signals.append(f"content:{cat}({ratio:.0%})")
            elif ratio > 0 and is_freetext:
                pass  # PII inline -> drape has_inline_pii, pas de categorisation pleine
        if dtype_kind in p["dtypes"]:
            s += 0.10
        else:
            s -= 0.15
        if _unicity_ok(uniq, *p["uniq"]):
            s += 0.15
        else:
            s -= 0.20
        scores[cat] = max(s, 0.0)

    # drapeau inline : texte libre contenant au moins un PII, sans categorisation pleine
    inline = False
    if is_freetext and n_s:
        for cat, p in PROFILES.items():
            if p["content"] and any(p["content"].search(v) for v in sample):
                inline = True; break

    if not scores or max(scores.values()) < THRESHOLD:
        return ColumnRisk(col, "none", round(max(scores.values(), default=0.0), 2),
                          signals, [], "conserver", False, inline)

    best = max(scores, key=scores.get)
    conf = round(min(scores[best], 0.99), 2)
    p = PROFILES[best]
    is_qi = (best == "quasi_id")
    ex = []
    if p["content"] is not None and n_s:
        ex = [_mask(v, best) for v in sample if p["content"].search(v)][:3]
    return ColumnRisk(col, best, conf, signals, ex, recommend_for(best, is_qi), is_qi, inline)

def analyze(df, sample_n=2000):
    return [score_column(c, df[c], sample_n) for c in df.columns]