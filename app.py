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

# 可选数据源（与 DataManager.FETCHER_MAP 对应）
DATA_SOURCE_OPTIONS = ["mock", "akshare", "baostock", "tushare"]
DATA_SOURCE_LABELS = {
    "mock":      "Mock (模拟)",
    "akshare":   "AKShare (A股/新浪)",
    "baostock":  "Baostock (免费/无Token)",
    "tushare":   "Tushare Pro (需Token)",
}


def mean(lst):
    return sum(lst) / len(lst) if lst else 0.0


st.set_page_config(page_title="AlphaPredator Dashboard", page_icon="📈", layout="wide")


st.sidebar.title("AlphaPredator")
st.sidebar.markdown("---")
st.sidebar.header("回测参数")
bt_start = st.sidebar.date_input("开始日期", date(2025, 1, 1))
bt_end = st.sidebar.date_input("结束日期", date(2025, 7, 1))
initial_capital = st.sidebar.number_input("初始资金", value=1000000, step=100000)
ds = st.sidebar.selectbox(
    "数据源",
    DATA_SOURCE_OPTIONS,
    index=0,
    format_func=lambda x: DATA_SOURCE_LABELS.get(x, x),
    help="选择数据来源: mock=模拟, akshare/baostock=真实A股数据, tushare=需要Token",
)
kelly_frac = st.sidebar.slider("凯利系数", 0.1, 1.0, 0.5, 0.05)
trail_stop = st.sidebar.slider("追踪止亏", 0.05, 0.20, 0.10, 0.01)
sig_thr = st.sidebar.slider("信号阈值", 0.10, 0.50, 0.25, 0.05)
run_btn = st.sidebar.button("运行回测", use_container_width=True, type="primary")


@st.cache_data(ttl=3600)
def run_bt(sym, seed, start, end):
    mgr = DataManager(source=ds)
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
    ohlcv = {"close": close, "high": bars["high"], "low": bars["low"],
             "open": bars["open"], "volume": bars["volume"]}
    sd = ag.compute_all(ohlcv)
    ascore = sd.get("alpha_scores", sd.get("alpha_score", []))
    asc = []
    for i in range(n):
        sub = {"close": close[max(0, i - 80):i + 1],
               "high": bars["high"][max(0, i - 80):i + 1],
               "low": bars["low"][max(0, i - 80):i + 1],
               "volume": bars["volume"][max(0, i - 80):i + 1]}
        r = aq.compute_anti_quant_score(**sub)
        asc.append(r["score"] / 100.0)
    comb = [ascore[i] * 0.6 + asc[i] * 0.4 for i in range(n)]
    regimes = rd.detect(close)
    mf = [0.0 if (r.value if hasattr(r, "value") else str(r)) in ("trend_down", "high_vol") else 1.0
          for r in regimes]
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
    res.update({"alpha_scores": ascore, "anti_scores": asc,
                "combined_scores": comb, "trade_signals": ts})
    res.update({"close_prices": close, "volumes": bars["volume"], "ohlcv": ohlcv})
    return res


DEFS = [
    ("STOCK_A",   42,  "强势趋势"),
    ("STOCK_B",  137,  "区间震荡"),
    ("STOCK_C",  256,  "反弹市"),
    ("STOCK_D",  999,  "高波动"),
    ("INDEX_300",  1,  "大盘基准"),
]


st.title("AlphaPredator Dashboard")
m1, m2, m3, m4, m5 = st.columns(5)
for col, (lbl, val) in zip([m1, m2, m3, m4, m5], [
    ("AlphaPredator", "散户反制量化"),
    ("模式", "回测/模拟"),
    ("数据源", ds.upper()),
    ("回测期", str(bt_start) + "~" + str(bt_end)),
    ("资金", "\u00a5" + "{:,.0f}".format(initial_capital)),
]):
    with col:
        st.metric(lbl, val)


if run_btn:
    st.cache_data.clear()
    results = {}
    pb = st.progress(0, text="运行中...")
    for i, (sym, seed, desc) in enumerate(DEFS):
        pb.progress((i + 1) / len(DEFS), text="回测 {}...".format(sym))
        r = run_bt(sym, seed, bt_start, bt_end)
        if r:
            results[sym] = r
    pb.empty()
    if results:
        ar  = mean([rv["total_return"]  for rv in results.values()])
        ash = mean([rv["sharpe_ratio"]  for rv in results.values()])
        am  = mean([rv["max_drawdown"]  for rv in results.values()])
        tt  = sum( rv["total_trades"]  for rv in results.values())
        aw  = mean([rv["win_rate"]      for rv in results.values()])
        s1, s2, s3, s4, s5 = st.columns(5)
        with s1: st.metric("平均收益",    "{:+.2%}".format(ar))
        with s2: st.metric("平均夏普",    "{:.2f}".format(ash))
        with s3: st.metric("平均最大回撤", "{:.2%}".format(am))
        with s4: st.metric("总交易次数",   "{}".format(tt))
        with s5: st.metric("平均胜率",     "{:.1%}".format(aw))
        st.markdown("---")
        st.subheader("权益曲线 & 信号")
        valid_tabs = [f"{s}({d})" for s, _, d in DEFS if s in results]
        tabs = st.tabs(valid_tabs if valid_tabs else ["无数据"])
        for ti, (sym, _, desc) in enumerate(DEFS):
            if sym not in results:
                continue
            with tabs[ti]:
                r = results[sym]
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1: st.metric("总收益",   "{:+.2%}".format(r["total_return"]))
                with k2: st.metric("年化",    "{:+.2%}".format(r["annualized_return"]))
                with k3: st.metric("夏普",    "{:.2f}".format(r["sharpe_ratio"]))
                with k4: st.metric("最大回撤", "{:.2%}".format(r["max_drawdown"]))
                with k5: st.metric("交易次数", "{}".format(r["total_trades"]))
                eq = r["equity_curve"]
                cp = r["close_prices"]
                n = len(cp)
                dates = [bt_start + timedelta(days=i) for i in range(n)]
                cr = [(e / eq[0] - 1) * 100 for e in eq] if eq else [0] * n
                fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                    vertical_spacing=0.04, row_heights=[0.35, 0.25, 0.20, 0.20])
                fig.add_trace(go.Scatter(x=dates, y=cp, mode="lines", name="收益价",
                              line=dict(color=ACCENT, width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=dates, y=[s * 100 for s in r["alpha_scores"]],
                              mode="lines", name="Alpha信号", line=dict(color="#4ECDC4", width=1.2),
                              fill="tozeroy", fillcolor="rgba(78,205,196,0.1)"), row=2, col=1)
                fig.add_trace(go.Scatter(x=dates, y=[s * 100 for s in r["anti_scores"]],
                              mode="lines", name="反量化", line=dict(color="#FFD166", width=1.2)),
                              row=2, col=1)
                if eq:
                    ne = [e / initial_capital * 100 for e in eq]
                    fig.add_trace(go.Scatter(x=dates, y=ne, mode="lines", name="权益%",
                                  line=dict(color="#06B6D4", width=2),
                                  fill="tozeroy", fillcolor="rgba(6,182,212,0.08)"), row=3, col=1)
                fig.add_trace(go.Scatter(x=dates, y=cr, mode="lines", name="累计收益%",
                              line=dict(color=ACCENT if cr[-1] >= 0 else DANGER, width=2),
                              fill="tozeroy",
                              fillcolor="rgba(0,200,150,0.06)" if cr[-1] >= 0
                              else "rgba(255,75,75,0.06)"), row=4, col=1)
                for i, sig in enumerate(r["trade_signals"]):
                    if sig != 0 and i > 0:
                        c = ACCENT if sig > 0 else DANGER
                        fig.add_annotation(x=dates[i], y=cp[i],
                                           text="▲" if sig > 0 else "▼",
                                           showarrow=True, arrowcolor=c, arrowsize=8,
                                           ax=0, ay=-20 if sig > 0 else 20,
                                           font=dict(color=c, size=14))
                fig.add_hline(y=0, line_dash="dot", line_color="#555", row=4, col=1)
                fig.update_layout(height=650, template="plotly_dark",
                                  plot_bgcolor=PLOT_BG, paper_bgcolor=PAPER_BG,
                                  font=dict(color="#E0E0E0", size=11), showlegend=True,
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                              xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
                                  xaxis_rangeslider_visible=False)
                fig.update_xaxes(gridcolor="#1E1E1E")
                fig.update_yaxes(gridcolor="#1E1E1E")
                st.plotly_chart(fig, use_container_width=True)
                if r["trades"]:
                    td = [{"方向": "做多" if t["direction"] > 0 else "做空",
                           "开仓价": "\u00a5{:.2f}".format(t["entry_price"]),
                           "平仓价": "\u00a5{:.2f}".format(t["price"]),
                           "数量": t["quantity"],
                           "盈亏": "\u00a5{:.2f}".format(t["pnl"])} for t in r["trades"]]
                    st.dataframe(td, use_container_width=True, hide_index=True)
    else:
        st.error("回测失败，请检查数据源")


with st.expander("系统说明"):
    st.markdown("**AlphaPredator** 散户反制量化系统  |  运行: `streamlit run app.py`")
    st.markdown("**数据源选项**: mock / akshare / baostock / tushare")
    st.markdown("**当前数据源**: **{}**".format(ds.upper()))
