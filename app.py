# -*- coding: utf-8 -*-
import sys, os, math
from datetime import date, timedelta
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _APP_DIR)

from data.fetcher import DataManager, MockFetcher
from signals.alpha_signals import AlphaSignalGenerator
from signals.regime_detector import RegimeDetector
from signals.anti_quant import AntiQuantEngine
from backtest.engine import BacktestEngine

ACCENT = "#00C896"
DANGER = "#FF4B4B"
PLOT_BG = "#0E1117"
PAPER_BG = "#161B22"

def mean(lst):
    return sum(lst) / len(lst) if lst else 0.0

st.set_page_config(page_title="AlphaPredator Dashboard", page_icon="\u0001f4c8", layout="wide")

st.sidebar.title("\u0001f4c8 AlphaPredator")
st.sidebar.markdown("---")
st.sidebar.header("\u56de\u6d4b\u53c2\u6570")
bt_start = st.sidebar.date_input("\u5f00\u59cb\u65e5\u671f", date(2025, 1, 1))
bt_end = st.sidebar.date_input("\u7ed3\u675f\u65e5\u671f", date(2025, 7, 1))
initial_capital = st.sidebar.number_input("\u521d\u59cb\u8d44\u91d1", value=1000000, step=100000)
ds = st.sidebar.selectbox("\u6570\u636e\u6e90", ["mock", "akshare"], 0)
kelly_frac = st.sidebar.slider("\u51ef\u5229\u7cfb\u6570", 0.1, 1.0, 0.5, 0.05)
trail_stop = st.sidebar.slider("\u8ffd\u8e2a\u6b62\u635f", 0.05, 0.20, 0.10, 0.01)
sig_thr = st.sidebar.slider("\u4fe1\u53f7\u9608\u503c", 0.10, 0.50, 0.25, 0.05)
run_btn = st.sidebar.button("\u8fd0\u884c\u56de\u6d4b", use_container_width=True, type="primary")

@st.cache_data(ttl=3600)
def run_bt(sym, seed, start, end):
    mgr = DataManager(ds)
    if ds == "mock":
        mgr.fetcher = MockFetcher(seed=seed)
    bars = mgr.get_bars(sym, start, end, "1D")
    if not bars or not bars.get("close") or len(bars["close"]) < 30:
        return None
    close = bars["close"]
    n = len(close)
    ag = AlphaSignalGenerator()
    rd = RegimeDetector()
    aq = AntiQuantEngine(trailing_stop_pct=trail_stop, cash_reserve_ratio=0.3)
    eng = BacktestEngine(initial_capital=initial_capital, commission_rate=0.0003, stamp_tax=0.001)
    ohlcv = {"close": close, "high": bars["high"], "low": bars["low"], "open": bars["open"], "volume": bars["volume"]}
    sd = ag.compute_all(ohlcv)
    ascore = sd.get("alpha_scores", sd.get("alpha_score", []))
    asc = []
    for i in range(n):
        sub = {"close": close[max(0, i - 80):i + 1], "high": bars["high"][max(0, i - 80):i + 1], "low": bars["low"][max(0, i - 80):i + 1], "volume": bars["volume"][max(0, i - 80):i + 1]}
        r = aq.compute_anti_quant_score(**sub)
        asc.append(r["score"] / 100.0)
    comb = [ascore[i] * 0.6 + asc[i] * 0.4 for i in range(n)]
    regimes = rd.detect(close)
    mf = [0.0 if (r.value if hasattr(r, "value") else str(r)) in ("trend_down", "high_vol") else 1.0 for r in regimes]
    ts = []
    for i in range(n):
        if comb[i] > sig_thr and mf[i] == 1.0:
            ts.append(1.0)
        elif comb[i] < -sig_thr:
            ts.append(-1.0)
        else:
            ts.append(0.0)
    res = eng.run(close, ts)
    res.update({"close_start": close[0], "close_end": close[-1], "data_days": n})
    res.update({"alpha_scores": ascore, "anti_scores": asc, "combined_scores": comb, "trade_signals": ts})
    res.update({"close_prices": close, "volumes": bars["volume"], "ohlcv": ohlcv})
    return res

DEFS = [("STOCK_A", 42, "\u5f3a\u52bf\u8d8a\u52bf"), ("STOCK_B", 137, "\u533a\u95f4\u632f\u8361"), ("STOCK_C", 256, "\u53cd\u5f39\u5e02"), ("STOCK_D", 999, "\u9ad8\u6ce2\u52a8"), ("INDEX_300", 1, "\u5927\u76d8\u57fa\u51c6")]

st.title("AlphaPredator Dashboard")
m1, m2, m3, m4, m5 = st.columns(5)
for col, (lbl, val) in zip([m1, m2, m3, m4, m5], [("AlphaPredator", "\u6563\u6237\u53cd\u5236\u91cf\u5316"), ("\u6a21\u5f0f", "\u56de\u6d4b/\u6a21\u62df"), ("\u6570\u636e\u6e90", ds.upper()), ("\u56de\u6d4b\u671f", str(bt_start) + "~" + str(bt_end)), ("\u8d44\u91d1", "\u00a5" + f"{initial_capital:,.0f}")]):
    with col:
        st.metric(lbl, val)

if run_btn:
    st.cache_data.clear()
    results = {}
    pb = st.progress(0, text="\u8fd0\u884c\u4e2d...")
    for i, (sym, seed, desc) in enumerate(DEFS):
        pb.progress((i + 1) / len(DEFS), text=f"\u56de\u6d4b {sym}...")
        r = run_bt(sym, seed, bt_start, bt_end)
        if r:
            results[sym] = r
    pb.empty()
    if results:
        ar = mean([r["total_return"] for r in results.values()])
        ash = mean([r["sharpe_ratio"] for r in results.values()])
        am = mean([r["max_drawdown"] for r in results.values()])
        tt = sum(r["total_trades"] for r in results.values())
        aw = mean([r["win_rate"] for r in results.values()])
        s1, s2, s3, s4, s5 = st.columns(5)
        with s1: st.metric("\u5e73\u5747\u6536\u76ca", f"{ar:+.2%}")
        with s2: st.metric("\u5e73\u5747\u590f\u666e", f"{ash:.2f}")
        with s3: st.metric("\u5e73\u5747\u6700\u5927\u56de\u6487", f"{am:.2%}")
        with s4: st.metric("\u603b\u4ea4\u6613\u6b21\u6570", f"{tt}")
        with s5: st.metric("\u5e73\u5747\u80dc\u7387", f"{aw:.1%}")
        st.markdown("---")
        st.subheader("\u0001f4c8 \u6743\u76ca\u66f2\u7ebf & \u4fe1\u53f7")
        tabs = st.tabs([f"{s}({d})" for s, _, d in DEFS if s in results] or ["\u65e0\u6570\u636e"])
        for ti, (sym, _, desc) in enumerate(DEFS):
            if sym not in results:
                continue
            with tabs[ti]:
                r = results[sym]
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1: st.metric("\u603b\u6536\u76ca", f"{r['total_return']:+.2%}")
                with k2: st.metric("\u5e74\u5316", f"{r['annualized_return']:+.2%}")
                with k3: st.metric("\u590f\u666e", f"{r['sharpe_ratio']:.2f}")
                with k4: st.metric("\u6700\u5927\u56de\u6487", f"{r['max_drawdown']:.2%}")
                with k5: st.metric("\u4ea4\u6613\u6b21\u6570", f"{r['total_trades']}")
                eq = r["equity_curve"]
                cp = r["close_prices"]
                n = len(cp)
                dates = [bt_start + timedelta(days=i) for i in range(n)]
                cr = [(e / eq[0] - 1) * 100 for e in eq] if eq else [0] * n
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04, row_heights=[0.35, 0.25, 0.20, 0.20])
                fig.add_trace(go.Scatter(x=dates, y=cp, mode="lines", name="\u6536\u76ca\u4ef7", line=dict(color=ACCENT, width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=dates, y=[s * 100 for s in r["alpha_scores"]], mode="lines", name="Alpha\u4fe1\u53f7", line=dict(color="#4ECDC4", width=1.2), fill="tozeroy", fillcolor="rgba(78,205,196,0.1)"), row=2, col=1)
                fig.add_trace(go.Scatter(x=dates, y=[s * 100 for s in r["anti_scores"]], mode="lines", name="\u53cd\u91cf\u5316", line=dict(color="#FFD166", width=1.2)), row=2, col=1)
                if eq:
                    ne = [e / initial_capital * 100 for e in eq]
                    fig.add_trace(go.Scatter(x=dates, y=ne, mode="lines", name="\u6743\u76ca%", line=dict(color="#06B6D4", width=2), fill="tozeroy", fillcolor="rgba(6,182,212,0.08)"), row=3, col=1)
                fig.add_trace(go.Scatter(x=dates, y=cr, mode="lines", name="\u7d2f\u8ba1\u6536\u76ca%", line=dict(color=ACCENT if cr[-1] >= 0 else DANGER, width=2), fill="tozeroy", fillcolor="rgba(0,200,150,0.06)" if cr[-1] >= 0 else "rgba(255,75,75,0.06)"), row=4, col=1)
                for i, sig in enumerate(r["trade_signals"]):
                    if sig != 0 and i > 0:
                        c = ACCENT if sig > 0 else DANGER
                        fig.add_annotation(x=dates[i], y=cp[i], text="\u25b2" if sig > 0 else "\u25bc", showarrow=True, arrowcolor=c, arrowsize=8, ax=0, ay=-20 if sig > 0 else 20, font=dict(color=c, size=14))
                fig.add_hline(y=0, line_dash="dot", line_color="#555", row=4, col=1)
                fig.update_layout(height=650, template="plotly_dark", plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG, font=dict(color="#E0E0E0", size=11), showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"), xaxis_rangeslider_visible=False)
                fig.update_xaxes(gridcolor="#1E1E1E")
                fig.update_yaxes(gridcolor="#1E1E1E")
                st.plotly_chart(fig, use_container_width=True)
                if r["trades"]:
                    td = [{"\u65b9\u5411": "\u505a\u591a" if t["direction"] > 0 else "\u505a\u7a7a", "\u5f00\u4ed3\u4ef7": f"\u00a5{t['entry_price']:.2f}", "\u5e73\u4ed3\u4ef7": f"\u00a5{t['price']:.2f}", "\u6570\u91cf": t["quantity"], "\u76c8\u4e8f": f"\u00a5{t['pnl']:.2f}"} for t in r["trades"]]
                    st.dataframe(td, use_container_width=True, hide_index=True)
        if len(results) >= 2:
            st.markdown("---")
            st.subheader("\u0001f510 \u6807\u7684\u5bf9\u6bd4")
            syms = list(results.keys())
            rets = [results[s]["total_return"] * 100 for s in syms]
            sharpes = [results[s]["sharpe_ratio"] for s in syms]
            mdds = [results[s]["max_drawdown"] * 100 for s in syms]
            colors = [ACCENT if r >= 0 else DANGER for r in rets]
            fig2 = make_subplots(rows=1, cols=3, subplot_titles=["\u6536\u76ca\u5bf9\u6bd4", "\u590f\u666e\u6bd4\u7387", "\u6700\u5927\u56de\u6487"])
            fig2.add_trace(go.Bar(x=syms, y=rets, marker_color=colors), row=1, col=1)
            fig2.add_trace(go.Bar(x=syms, y=sharpes, marker_color="#4ECDC4"), row=1, col=2)
            fig2.add_trace(go.Bar(x=syms, y=mdds, marker_color="#FF6B6B"), row=1, col=3)
            fig2.update_layout(template="plotly_dark", plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG, font=dict(color="#E0E0E0"), showlegend=False, height=280)
            fig2.update_xaxes(gridcolor="#1E1E1E")
            fig2.update_yaxes(gridcolor="#1E1E1E")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.error("\u56de\u6d4b\u5931\u8d25\uff0c\u8bf7\u68c0\u67e5\u6570\u636e\u6e90")

with st.expander("\u2139\ufe0f \u7cfb\u7edf\u8bf4\u660e"):
    st.markdown("**AlphaPredator** \u6563\u6237\u53cd\u5236\u91cf\u5316\u7cfb\u7edf  |  \u8fd0\u884c: `streamlit run app.py`")
