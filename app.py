import streamlit as st
from pathlib import Path
from html import escape
from core import io as cio, detection, risk as crank, report
from i18n.catalog import t
from ui.icons import svg, PAGE_ICON
from ui.components import (
    page_header,
    section,
    card,
    kv_grid,
    warn_box,
    ok_box,
    info_box,
    err_box,
    md_bold_to_html,
)

ROOT = Path(__file__).parent
CSS = (ROOT / "ui" / "style.css").read_text(encoding="utf-8")
CSS += "\n" + (ROOT / "assets" / "suite.css").read_text(encoding="utf-8")
BRAND_HTML = (ROOT / "ui" / "sidebar.html").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "dev"

st.set_page_config(page_title="Privacy Risk Lens", layout="wide", page_icon=PAGE_ICON)
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

for k, v in (("lang", "fr"), ("page", "home")):
    st.session_state.setdefault(k, v)
L = st.session_state.lang


def fill(html, lang):
    """Remplace les placeholders {{cle}} par la traduction (HTML-safe)."""
    out = html
    i = 0
    while "{{" in out:
        a = out.find("{{"); b = out.find("}}", a)
        if b == -1:
            break
        key = out[a + 2:b].strip()
        out = out[:a] + t(key, lang) + out[b + 2:]
        i += 1
        if i > 200:
            break
    return out


def alert(kind, msg):
    """Bandeau unifié HTML+SVG."""
    if kind == "warning":
        warn_box(msg)
    elif kind == "success":
        ok_box(msg)
    elif kind == "error":
        err_box(msg)
    else:
        info_box(msg)


TABS = [("home", "nav.home"), ("import", "nav.import"), ("overview", "nav.overview"),
        ("detection", "nav.detection"), ("risk", "nav.risk"), ("report", "nav.report")]
labels = [t(lbl, L) for _, lbl in TABS]
idx = next((i for i, (k, _) in enumerate(TABS) if k == st.session_state.page), 0)
view_keys = [key for key, _ in TABS]
with st.container(key="suite-topbar"):
    nav_col, language_col, brand_col = st.columns([6.7, 1.1, 2.2])
    with nav_col:
        st.session_state.page = st.segmented_control(
            "nav",
            view_keys,
            default=view_keys[idx],
            format_func=lambda key: t(dict(TABS)[key], L),
            label_visibility="collapsed",
            key="suite-nav",
            required=True,
            width="stretch",
        )
    with language_col:
        st.segmented_control(
            t("lang.label", L),
            options=["fr", "en"],
            format_func=lambda value: value.upper(),
            label_visibility="collapsed",
            key="lang",
            required=True,
        )
    with brand_col:
        brand = fill(BRAND_HTML.replace("{{icon_shield}}", svg("shield", 22))
                     .replace("{{version}}", VERSION), L)
        st.markdown(brand, unsafe_allow_html=True)


def head(tk, sk):
    page_header(t(tk, L), t(sk, L))


# ---------------- pages ----------------
if st.session_state.page == "home":
    page_header("Privacy Risk Lens", t("home.sub", L))
    section(t("home.howto", L))
    steps = "".join(f"<li>{md_bold_to_html(t(k, L))}</li>" for k in ("home.step1", "home.step2", "home.step3"))
    card(f"<ol>{steps}</ol>")
    section(t("home.state", L))
    df = st.session_state.get("df")
    dets = st.session_state.get("dets")
    risk_res = st.session_state.get("risk_res")
    kv_grid([
        (t("home.rows", L), (f"{len(df):,}".replace(",", " ") if df is not None else "-")),
        (t("import.cols", L), (len(df.columns) if df is not None else "-")),
        (t("overview.sens", L), (str(len([d for d in dets if d.category != "none"])) if dets is not None else "-")),
        (t("overview.level", L), (crank.overall_risk(dets, risk_res)["level"].upper() if dets is not None else "-")),
    ])
    if df is None:
        warn_box(t("home.no_data", L))
    else:
        ok_box(f"{len(df):,} {t('home.rows', L)} · {t('home.sampled' if st.session_state.get('sampled') else 'home.full', L)}")


elif st.session_state.page == "import":
    head("import.title", "import.sub")
    with st.expander(t("import.ioopts", L), expanded=False):
        max_rows_full = st.number_input(t("opt.max_rows_full", L), min_value=100, max_value=2000000,
                                        value=300000, step=10000, help=t("opt.max_rows_full_help", L),
                                        key="opt_max_rows_full")
        sample_n = st.number_input(t("opt.sample_n", L), min_value=100, max_value=2000000,
                                   value=200000, step=10000, help=t("opt.sample_n_help", L),
                                   key="opt_sample_n")
        sep_map = {"sep_auto": "auto", "sep_comma": ",", "sep_semicolon": ";", "sep_tab": "\t", "sep_pipe": "|"}
        sep_label = st.selectbox(t("opt.separator", L), list(sep_map.keys()), index=0,
                                 help=t("opt.separator_help", L), key="opt_sep_label",
                                 format_func=lambda k: t(f"sep.{k}", L))
        enc_options = ["auto", "utf-8", "utf-8-sig", "latin1", "cp1252"]
        enc_value = st.selectbox(t("opt.encoding", L), enc_options, index=0,
                                 help=t("opt.encoding_help", L), key="opt_enc")
        sep_value = sep_map[sep_label]
    up = st.file_uploader(t("import.drop", L), type=["csv"], key="uploader")
    if up is not None:
        upload_id = getattr(up, "file_id", None) or (up.name, up.size)
        opt_change_id = (max_rows_full, sample_n, sep_value, enc_value)
        full_id = (upload_id, opt_change_id)
        if st.session_state.get("_upload_id") != full_id:
            for key in ("df", "total", "sampled", "dets", "risk_res", "gen", "_upload_error",
                        "_upload_enc", "_upload_sep", "_upload_cols", "_upload_schema"):
                st.session_state.pop(key, None)
            st.session_state["_upload_id"] = full_id
            try:
                data = up.getvalue()
                enc, sep, cols = cio.sniff(data, enc_hint=None if enc_value == "auto" else enc_value,
                                           sep_hint=None if sep_value == "auto" else sep_value)
                df, total, sampled = cio.load_sampled(data, sep, enc,
                                                      max_rows_full=int(max_rows_full),
                                                      sample_n=int(sample_n))
                schema = [{"col": c, "dtype": str(df[c].dtype),
                           "nonnull": int(df[c].notna().sum()),
                           "uniq": int(df[c].nunique(dropna=True))} for c in df.columns]
                st.session_state.update(df=df, total=total, sampled=sampled,
                                        _upload_enc=enc, _upload_sep=sep, _upload_cols=cols,
                                        _upload_schema=schema)
            except ValueError as e:
                st.session_state["_upload_error"] = {
                    "empty": "err.empty", "nocols": "err.no_cols"}.get(str(e), "err.parse")
            except Exception:
                st.session_state["_upload_error"] = "err.parse"

        if st.session_state.get("_upload_error"):
            alert("error", t(st.session_state["_upload_error"], L))
        elif "df" in st.session_state:
            enc, sep, cols = (st.session_state["_upload_enc"], st.session_state["_upload_sep"],
                              st.session_state["_upload_cols"])
            df = st.session_state.df
            st.markdown(f"<div class='prl-card'><b>{t('import.meta', L)}</b> : "
                        f"{t('import.enc', L)}=<code>{enc}</code> · "
                        f"{t('import.sep', L)}=<code>{repr(sep)}</code> · "
                        f"{t('import.cols', L)}={len(cols)}</div>", unsafe_allow_html=True)
            section(t('import.preview', L))
            preview = df.head(8).apply(lambda column: column.map(lambda _: "•"))
            st.dataframe(preview, width="stretch", hide_index=True)
            schema = [{t("import.col", L): row["col"], t("import.dtype", L): row["dtype"],
                       t("import.nonnull", L): row["nonnull"], t("import.uniq", L): row["uniq"]}
                      for row in st.session_state._upload_schema]
            section(t('import.schema', L))
            st.dataframe(schema, width="stretch", hide_index=True)
            if st.button(t("import.run", L), type="primary"):
                with st.spinner(t("import.analyzing", L)):
                    dets = detection.analyze(df)
                    qis = crank.qi_columns(dets)
                    st.session_state.dets = dets
                    st.session_state.risk_res = crank.k_anonymity(df, qis) if qis else None
                    st.session_state.gen = crank.suggest_generalization(df, qis) if qis else None
                ok_box(t("import.done", L))
    elif "df" in st.session_state:
        card(t('import.session_info', L).format(count=len(st.session_state.df)))
        if st.button(t("import.clear", L), key="clear_dataset"):
            for key in ("df", "total", "sampled", "dets", "risk_res", "gen", "_upload_id",
                        "_upload_error", "_upload_enc", "_upload_sep", "_upload_cols", "_upload_schema"):
                st.session_state.pop(key, None)
            st.rerun()
elif st.session_state.page == "overview":
    head("overview.title", "overview.sub")
    if "dets" not in st.session_state:
        warn_box(t("err.need_data", L))
    else:
        ov = crank.overall_risk(st.session_state.dets, st.session_state.get("risk_res"))
        kres = st.session_state.get("risk_res")
        section(t("overview.title", L))
        kv_grid([
            (t("overview.score", L), f"{ov['score']}/100"),
            (t("overview.level", L), t("overview.level." + ov["level"], L)),
            (t("overview.sens", L), str(ov["n_sensitive"])),
            (t("overview.kmin", L), str(kres["k_min"]) if kres else "-"),
        ])
        section(t("overview.by_cat", L))
        cats = {}
        for d in st.session_state.dets:
            cats[d.category] = cats.get(d.category, 0) + 1
        st.bar_chart({t(f"cat.{c}", L): v for c, v in cats.items()})

elif st.session_state.page == "detection":
    head("detection.title", "detection.sub")
    if "dets" not in st.session_state:
        warn_box(t("err.need_data", L))
    elif not [d for d in st.session_state.dets if d.category != "none"]:
        ok_box(t("detection.none_msg", L))
    else:
        tbl = [{t("detection.col", L): d.column, t("detection.cat", L): t(f"cat.{d.category}", L),
            t("detection.conf", L): d.confidence,
            t("detection.qi", L): "✓" if d.is_quasi_id else "",
            t("detection.inline", L): "✓" if d.has_inline_pii else "",
            t("detection.examples", L): ", ".join(d.examples_masked),
            t("detection.signals", L): ", ".join(d.signals),
            t("detection.reco", L): t(d.recommendation, L)} for d in st.session_state.dets]
        st.dataframe(tbl, width="stretch", hide_index=True)

elif st.session_state.page == "risk":
    head("risk.title", "risk.sub")
    if "dets" not in st.session_state:
        warn_box(t("err.need_data", L))
    else:
        kres, gen = st.session_state.get("risk_res"), st.session_state.get("gen")
        if not kres:
            warn_box(t("risk.no_qi", L))
        else:
            card(f"<b>{t('risk.statement', L)}</b><br>{escape(crank.risk_statement(kres, L).replace('`', ''))}")
            section(t("risk.title", L))
            kv_grid([
                (t("risk.kmin", L), str(kres["k_min"])),
                (t("risk.frac_unique", L), f"{kres['frac_unique']:.0%}"),
                (t("risk.kafter", L), str(gen["k_after"]) if gen and gen.get("k_after") is not None else "-"),
            ])
            if kres.get("worst_combinations"):
                section(t("risk.worst", L))
                st.dataframe([{t("risk.combo", L): f"{t('risk.combo', L)} {i}",
                               t("risk.size", L): v}
                              for i, v in kres["worst_combinations"].items()],
                             width="stretch", hide_index=True)
            if gen and gen.get("applied"):
                section(t("risk.gen_applied", L))
                st.dataframe([{t("risk.gen_col", L): row["column"],
                               t("risk.gen_rule", L): row["rule"]} for row in gen["applied"]],
                             width="stretch", hide_index=True)

elif st.session_state.page == "report":
    head("report.title", "report.sub")
    if "dets" not in st.session_state:
        warn_box(t("err.need_data", L))
    else:
        fmt = st.selectbox(t("report.format", L), ["markdown", "json", "html"],
                           format_func=lambda x: t({"markdown": "report.r_md", "json": "report.r_json",
                                                    "html": "report.r_html"}[x], L))
        blob = report.build(st.session_state.dets, st.session_state.get("df"), L, fmt, VERSION,
                            st.session_state.get("risk_res"), st.session_state.get("gen"))
        ext = {"markdown": "md", "json": "json", "html": "html"}[fmt]
        st.download_button(t("report.download", L), blob, file_name=f"privacy-report.{ext}",
                           mime="text/plain")
        if fmt == "html":
            st.iframe(blob, height=420)
        else:
            st.code(blob, language="markdown" if fmt == "markdown" else fmt)