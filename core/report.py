import json
from html import escape
from dataclasses import asdict
from .recommend import reco_detail
from . import risk as _risk
from i18n.catalog import t

def _html(value):
    return escape(str(value), quote=True)

def _rows(dets, lang):
    out = []
    for d in dets:
        ak, dk = reco_detail(d.category)
        out.append({
            "column": d.column,
            "category": t(f"cat.{d.category}", lang),
            "confidence": d.confidence,
            "is_quasi_id": d.is_quasi_id,
            "has_inline_pii": d.has_inline_pii,
            "signals": d.signals,
            "examples_masked": d.examples_masked,
            "action": t(ak, lang),
            "detail": t(dk, lang),
        })
    return out

def build(dets, df, lang, fmt, version, kres=None, gen=None):
    rows = _rows(dets, lang)
    ov = _risk.overall_risk(dets, kres)
    stmt = _risk.risk_statement(kres, lang)
    title = t("app.title", lang)
    disc = t("disclaimer", lang)

    if fmt == "json":
        payload = {
            "tool": title, "version": version, "language": lang,
            "disclaimer": disc,
            "overview": ov,
            "columns": rows,
            "risk": kres, "generalization": gen, "risk_statement": stmt,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    if fmt == "html":
        trs = "".join(
            f"<tr><td><code>{_html(r['column'])}</code></td><td>{_html(r['category'])}</td>"
            f"<td>{r['confidence']:.2f}</td><td>{_html(r['action'])}</td>"
            f"<td>{_html(', '.join(r['examples_masked']) or '-')}</td>"
            f"<td>{_html(', '.join(r['signals']) or '-')}</td></tr>" for r in rows)
        genrows = ""
        if gen and gen.get("applied"):
            genrows = ("<h3>" + _html(t("risk.gen_applied", lang)) + "</h3><table><tr><th>" +
                       _html(t("risk.gen_col", lang)) + "</th><th>" + _html(t("risk.gen_rule", lang)) +
                       "</th></tr>" +
                       "".join(f"<tr><td><code>{_html(a['column'])}</code></td>"
                               f"<td>{_html(a['rule'])}</td><td>-</td></tr>" for a in gen["applied"]) +
                       "</table>")
        worst = ""
        if kres and kres.get("worst_combinations"):
            worst = ("<h3>" + _html(t("risk.worst", lang)) + "</h3><ul>" +
                     "".join(f"<li><code>{_html(t('risk.combo', lang))} {i}</code> : {_html(v)}</li>"
                             for i, v in kres["worst_combinations"].items()) + "</ul>")
        return ("<!doctype html><meta charset='utf-8'><title>" + _html(title) + "</title>"
                "<style>body{font-family:system-ui,sans-serif;margin:2rem;color:#0f172a}"
                "table{border-collapse:collapse;width:100%}th,td{border:1px solid #e5e7eb;"
                "padding:.4rem .6rem;text-align:left;font-size:.9rem}th{background:#f1f5f9}"
                "code{background:#f1f5f9;padding:0 .25rem;border-radius:4px}"
                ".disc{color:#64748b;font-size:.85rem;border-left:3px solid #cbd5e1;padding-left:.8rem}"
                ".score{font-size:2rem;font-weight:800}</style>"
                f"<h1>{_html(title)}</h1><div class='disc'>{_html(disc)} · v{_html(version)}</div>"
                f"<p class='score'>{ov['score']}/100 · {t('overview.level.'+ov['level'], lang)}</p>"
                f"<p>{_html(stmt or '-')}</p>"
                "<h3>" + t("detection.title", lang) + "</h3>"
                "<table><tr><th>" + t("detection.col", lang) + "</th><th>" + t("detection.cat", lang) +
                "</th><th>" + t("detection.conf", lang) + "</th><th>" + t("detection.reco", lang) +
                "</th><th>" + t("detection.examples", lang) + "</th><th>" + t("detection.signals", lang) +
                "</th></tr>" + trs + "</table>" + genrows + worst)

    # markdown (defaut)
    md = [f"# {title}", f"> {disc} · v{version}", "",
          f"**{t('overview.score', lang)} : {ov['score']}/100 · "
          f"{t('overview.level.'+ov['level'], lang)}**", ""]
    if stmt:
        md += [f"**{t('risk.statement', lang)}** : {escape(stmt)}", ""]
    md += [f"## {t('detection.title', lang)}", "",
           f"| {t('detection.col', lang)} | {t('detection.cat', lang)} | "
           f"{t('detection.conf', lang)} | {t('detection.reco', lang)} | "
           f"{t('detection.examples', lang)} | {t('detection.signals', lang)} |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {_risk._md_code(r['column'])} | {r['category']} | {r['confidence']:.2f} | "
                  f"{r['action']} | {', '.join(r['examples_masked']) or '-'} | "
                  f"{', '.join(r['signals']) or '-'} |")
    if gen and gen.get("applied"):
        md += ["", f"## {t('risk.gen_applied', lang)}", ""]
        for a in gen["applied"]:
            md.append(f"- {_risk._md_code(a['column'])} -> **{a['rule']}**")
        if gen.get("k_after") is not None:
            md.append(f"- {t('risk.kafter', lang)} : **{gen['k_after']}**")
    if kres and kres.get("worst_combinations"):
        md += ["", f"## {t('risk.worst', lang)}", ""]
        for k, v in kres["worst_combinations"].items():
            md.append(f"- {_risk._md_code(t('risk.combo', lang) + ' ' + k)} : {v}")
    md += ["", f"## {t('report.title', lang)} — {t('reco.action.anonymiser', lang)} / "
           f"{t('reco.action.agreger', lang)} / {t('reco.action.supprimer', lang)}", ""]
    for r in rows:
        if r["category"] != t("cat.none", lang):
            md.append(f"- `{r['column']}` : **{r['action']}** — {r['detail']}")
    return "\n".join(md)