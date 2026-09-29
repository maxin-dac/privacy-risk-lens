import re
import pandas as pd
from i18n.catalog import t

QI_CATS = {"quasi_id", "address"}

def qi_columns(detections):
    return [d.column for d in detections if d.is_quasi_id or d.category in QI_CATS]

def k_anonymity(df, qis, threshold=5):
    if not qis:
        return None
    sub = df[qis]
    sizes = sub.groupby(qis, dropna=False, sort=False).size()
    k_min = int(sizes.min())
    frac_unique = float(sizes[sizes == 1].sum() / len(sub))
    if k_min < threshold:
        risk = "eleve"
    elif k_min < 2 * threshold:
        risk = "moyen"
    else:
        risk = "faible"
    worst = sizes[sizes < threshold].sort_values().head(10)
    return {"qis": qis, "k_min": k_min, "frac_unique": frac_unique,
            "risk": risk, "threshold": threshold,
            "worst_combinations": {str(i): int(v) for i, v in enumerate(worst, 1)}}


_GEN_RULES = [
    (r"(naissance|dob|birth|date_?nais)", "year",
     lambda s: pd.to_datetime(s, errors="coerce").dt.year.astype("string")),
    (r"(code_?postal|zip|\bcp\b)", "zip2",
     lambda s: s.astype(str).str.extract(r"(\d{2})")[0]),
    (r"(\bage\b|age_)", "ageband",
     lambda s: (pd.to_numeric(s, errors="coerce") // 10 * 10).astype("string")),
    (r"(ville|city|town|commune)", "region", lambda s: "agrege"),
    (r"(region|departement|dept)", "region", lambda s: "agrege"),
]

def _gen_one(col, series):
    cn = col.lower()
    for pat, rule, fn in _GEN_RULES:
        if re.search(pat, cn):
            try:
                return fn(series), rule
            except Exception:
                return None, rule
    return None, None

def suggest_generalization(df, qis):
    applied, tmp = [], df[qis].copy()
    for c in qis:
        new, rule = _gen_one(c, df[c])
        if new is not None:
            tmp[c] = new
            applied.append({"column": c, "rule": rule})
    if not applied:
        return {"applied": [], "k_after": None}
    sizes = tmp.groupby(qis, dropna=False, sort=False).size()
    return {"applied": applied, "k_after": int(sizes.min())}

def _md_code(value):
    text = str(value).replace("\r", " ").replace("\n", " ").replace("|", "&#124;")
    runs = re.findall(r"`+", text)
    fence = "`" * (max(map(len, runs), default=0) + 1)
    return f"{fence} {text} {fence}"

def risk_statement(res, lang="fr"):
    if not res:
        return ""
    combo = " + ".join(_md_code(c) for c in res["qis"])
    pct = f"{res['frac_unique']:.0%}"
    lvl = t(f"overview.level.{res['risk']}", lang)
    if lang == "en":
        return (f"The combination {combo} leaves {pct} of rows unique (k={res['k_min']}) "
                f"-> re-identification risk: {lvl}.")
    return (f"La combinaison {combo} laisse {pct} des lignes uniques (k={res['k_min']}) "
            f"-> risque de re-identification : {lvl}.")

def overall_risk(dets, kres):
    n = max(len(dets), 1)
    sens = [d for d in dets if d.category != "none"]
    prop = len(sens) / n
    conf_mean = (sum(d.confidence for d in sens) / len(sens)) if sens else 0.0
    if kres:
        rf = 1.0 if kres["k_min"] < kres["threshold"] else (0.5 if kres["k_min"] < 2 * kres["threshold"] else 0.0)
    else:
        rf = 0.0
    score = round(100 * (0.45 * prop + 0.35 * conf_mean + 0.20 * rf))
    level = "eleve" if score >= 66 else ("moyen" if score >= 33 else "faible")
    return {"score": score, "level": level, "n_sensitive": len(sens),
            "n_qi": len([d for d in dets if d.is_quasi_id or d.category in QI_CATS]),
            "conf_mean": round(conf_mean, 2)}