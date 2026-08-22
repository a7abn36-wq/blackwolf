"""Black Wolf - Multi-Agent AI Trading System
Professional Gold (XAU/USD) Analysis Platform"""

import streamlit as st
import json
import os
import time
import pandas as pd
from datetime import datetime
from io import StringIO

st.set_page_config(
    page_title="Black Wolf | AI Trading System",
    page_icon="🐺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports ──
from agents import (
    run_full_analysis, get_analysis_history, get_stats,
    run_research_review, AGENTS, format_market_data, init_db,
)

# ── Theme CSS ──
st.markdown("""
<style>
/* ── Global ── */
.stApp {
    background: linear-gradient(135deg, #0a0a0f 0%, #0d1117 50%, #0a0e1a 100%);
    color: #e0e0e0;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #0a0e1a 100%);
    border-right: 1px solid rgba(0, 240, 255, 0.15);
}
section[data-testid="stSidebar"] .stMarkdown { color: #b0b0b0; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: rgba(0, 240, 255, 0.05);
    border: 1px solid rgba(0, 240, 255, 0.2);
    border-radius: 8px;
    color: #888;
    padding: 10px 24px;
    font-weight: 600;
    transition: all 0.3s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    background: rgba(0, 240, 255, 0.1);
    color: #00f0ff;
    border-color: rgba(0, 240, 255, 0.4);
}
.stTabs [aria-selected="true"] {
    background: rgba(0, 240, 255, 0.15) !important;
    color: #00f0ff !important;
    border-color: #00f0ff !important;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.2), inset 0 0 20px rgba(0, 240, 255, 0.05);
}

/* ── Cards ── */
.bw-card {
    background: linear-gradient(135deg, rgba(13, 17, 23, 0.9), rgba(10, 14, 26, 0.9));
    border: 1px solid rgba(0, 240, 255, 0.15);
    border-radius: 12px;
    padding: 20px;
    margin: 10px 0;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}
.bw-card:hover {
    border-color: rgba(0, 240, 255, 0.3);
    box-shadow: 0 4px 30px rgba(0, 240, 255, 0.1);
}

/* ── Signal Badge ── */
.signal-buy {
    background: linear-gradient(135deg, rgba(0, 255, 136, 0.15), rgba(0, 200, 100, 0.1));
    border: 2px solid rgba(0, 255, 136, 0.6);
    color: #00ff88;
    text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
}
.signal-sell {
    background: linear-gradient(135deg, rgba(255, 50, 50, 0.15), rgba(200, 0, 0, 0.1));
    border: 2px solid rgba(255, 50, 50, 0.6);
    color: #ff3232;
    text-shadow: 0 0 20px rgba(255, 50, 50, 0.5);
}
.signal-hold {
    background: linear-gradient(135deg, rgba(255, 200, 0, 0.15), rgba(200, 150, 0, 0.1));
    border: 2px solid rgba(255, 200, 0, 0.6);
    color: #ffc800;
    text-shadow: 0 0 20px rgba(255, 200, 0, 0.5);
}

/* ── Metric Cards ── */
.bw-metric {
    text-align: center;
    padding: 15px;
    background: rgba(0, 240, 255, 0.05);
    border: 1px solid rgba(0, 240, 255, 0.15);
    border-radius: 10px;
}
.bw-metric .value {
    font-size: 1.8em;
    font-weight: 800;
    color: #00f0ff;
    text-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
}
.bw-metric .label {
    font-size: 0.85em;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 5px;
}

/* ── Agent Status ── */
.agent-ok { color: #00ff88; }
.agent-error { color: #ff3232; }
.agent-waiting { color: #ffc800; }

/* ── Progress Bar ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #00f0ff, #00c8ff, #00f0ff);
    box-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00f0ff, #0080ff);
    color: #000;
    font-weight: 700;
    border: none;
    border-radius: 8px;
    padding: 12px 32px;
    font-size: 1.1em;
    text-transform: uppercase;
    letter-spacing: 2px;
    transition: all 0.3s ease;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 40px rgba(0, 240, 255, 0.6);
    transform: translateY(-2px);
}

/* ── Dataframes ── */
.dataframe th {
    background: rgba(0, 240, 255, 0.1) !important;
    color: #00f0ff !important;
    border-bottom: 1px solid rgba(0, 240, 255, 0.3) !important;
}
.dataframe td {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
    color: #ccc !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: rgba(0, 240, 255, 0.05);
    border: 1px solid rgba(0, 240, 255, 0.15);
    border-radius: 8px;
    color: #00f0ff;
}

/* ── File Uploader ── */
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(0, 240, 255, 0.3);
    border-radius: 12px;
    background: rgba(0, 240, 255, 0.03);
}

/* ── Wolf Logo ── */
.wolf-logo {
    font-size: 2.5em;
    text-align: center;
    margin: 10px 0;
}
.wolf-title {
    text-align: center;
    font-size: 2em;
    font-weight: 900;
    background: linear-gradient(135deg, #00f0ff, #0080ff, #00f0ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: 8px;
    text-transform: uppercase;
}
.wolf-subtitle {
    text-align: center;
    color: #444;
    font-size: 0.9em;
    letter-spacing: 4px;
    text-transform: uppercase;
}

/* ── Hide default elements ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ──
st.markdown("""
<div class="wolf-logo">🐺</div>
<div class="wolf-title">BLACK WOLF</div>
<div class="wolf-subtitle">Multi-Agent AI Trading System &bull; XAU/USD</div>
""", unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid rgba(0, 240, 255, 0.2); margin: 15px 0;'>", unsafe_allow_html=True)


# ── Sidebar ──
st.sidebar.markdown("### ⚙️ System")
st.sidebar.caption("Entry: M5 | Analysis: H1+")

with st.sidebar.expander("📡 API Status", expanded=True):
    st.markdown("**🐺 DeepSeek V3**\nSMC Technical Analyst")
    st.markdown("**🛡️ Mistral**\nRisk Manager")
    st.markdown("**📊 Llama 3.3 70B**\nMarket Analyst")
    st.markdown("**🌍 Qwen 2.5 72B**\nMacro Analyst")
    st.markdown("**👑 DeepSeek R1**\nDecision Maker")

with st.sidebar.expander("📊 Quick Stats"):
    stats = get_stats()
    st.metric("Total Analyses", stats["total"])
    st.metric("Avg Confidence", f"{stats['avg_confidence']}%")
    c1, c2 = st.sidebar.columns(2)
    c1.metric("BUY", stats["buy"])
    c2.metric("SELL", stats["sell"])


# ── CSV Parser ──
def parse_csv(file):
    raw = file.read()
    if raw[:2] == b'\xff\xfe':
        text = raw.decode('utf-16-le')
    elif raw[:3] == b'\xef\xbb\xbf':
        text = raw.decode('utf-8-sig')
    else:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('utf-16-le')
    text = text.lstrip('\ufeff')
    header = text.strip().split('\n')[0]
    sep = '\t' if '\t' in header else ','
    df = pd.read_csv(StringIO(text), sep=sep, on_bad_lines='skip')
    df.columns = [c.replace('\ufeff', '').strip().lower() for c in df.columns]

    dt_col = None
    for c in ['date', 'datetime', '<date>']:
        if c in df.columns:
            dt_col = c
            break
    if dt_col is None:
        for c in df.columns:
            if c not in ['open', 'high', 'low', 'close', 'volume', 'tick_volume']:
                dt_col = c
                break
    if dt_col and 'time' not in df.columns:
        dt = pd.to_datetime(df[dt_col], format='%Y.%m.%d %H:%M', errors='coerce')
        df['date'] = dt.dt.strftime('%Y.%m.%d')
        df['time'] = dt.dt.strftime('%H:%M')
    if dt_col and dt_col != 'date' and dt_col in df.columns:
        df = df.drop(columns=[dt_col])
    if 'time' not in df.columns:
        df['time'] = '00:00'

    vol = 'tick_volume' if 'tick_volume' in df.columns else ('volume' if 'volume' in df.columns else None)
    if vol:
        df['volume'] = df[vol]
    if 'volume' not in df.columns:
        df['volume'] = 0

    cols = [c for c in ['date', 'time', 'open', 'high', 'low', 'close', 'volume'] if c in df.columns]
    df = df[cols].dropna(subset=['open', 'high', 'low', 'close'])
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna().reset_index(drop=True)


def manual_analysis():
    """Tab 1: Live Analysis with manual data entry or CSV."""
    st.markdown('<div class="bw-card"><h2 style="color:#00f0ff;">🐺 Live Analysis</h2><p style="color:#666;">Upload MT5 data or enter price manually for multi-agent SMC analysis</p></div>', unsafe_allow_html=True)

    mode = st.radio("Data Source", ["📁 Upload MT5 CSV", "✏️ Manual Entry"], horizontal=True)

    candles = None
    current_price = None

    if mode == "📁 Upload MT5 CSV":
        f = st.file_uploader("Upload XAUUSD M5 CSV", type=["csv"])
        if f:
            df = parse_csv(f)
            st.success(f"Loaded {len(df):,} candles")
            n_candles = st.slider("Number of candles to send", 20, 100, 50, key="csv_candles")
            candles = df.tail(n_candles)[['open', 'high', 'low', 'close', 'volume']].to_dict('records')
            current_price = df['close'].iloc[-1]
            st.markdown(f"**Current Price:** `{current_price:.2f}` | **Range:** `{df['date'].iloc[0]}` ~ `{df['date'].iloc[-1]}`")

    else:
        st.markdown("#### Enter Current Market Data")
        col1, col2, col3 = st.columns(3)
        current_price = col1.number_input("Current Price", value=2495.00, step=0.01, format="%.2f")
        period_high = col2.number_input("Period High", value=2510.00, step=0.01, format="%.2f")
        period_low = col3.number_input("Period Low", value=2470.00, step=0.01, format="%.2f")

        st.markdown("#### Recent Candles (paste OHLCV, one per line)")
        candle_input = st.text_area("",
            placeholder="O,H,L,C,V\n2480.5,2485.2,2478.1,2483.8,1200\n2483.8,2488.0,2482.0,2487.5,980\n...",
            height=200, key="manual_candles")

        if candle_input.strip():
            candles = []
            for line in candle_input.strip().split('\n'):
                parts = [x.strip() for x in line.split(',')]
                if len(parts) >= 4:
                    candles.append({
                        'open': float(parts[0]), 'high': float(parts[1]),
                        'low': float(parts[2]), 'close': float(parts[3]),
                        'volume': float(parts[4]) if len(parts) > 4 else 0
                    })

    if st.button("🐺  RUN BLACK WOLF ANALYSIS", type="primary", use_container_width=True):
        if not candles:
            st.error("No data provided!")
            return

        with st.spinner("🐺 Wolves are analyzing..."):
            progress = st.progress(0, text="Phase 1: Independent agent analysis...")
            try:
                result = run_full_analysis(candles, current_price=current_price)
                progress.progress(100, text="Analysis complete!")

                if result.get("success") == False:
                    st.error(result.get("error", "Unknown error"))
                    if result.get("errors"):
                        for err in result["errors"]:
                            st.warning(err)
                    return

                # Display results
                st.session_state['last_analysis'] = result

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

    # Display last analysis
    if 'last_analysis' in st.session_state:
        r = st.session_state['last_analysis']
        display_analysis_results(r)


def display_analysis_results(r):
    """Render the analysis results beautifully."""
    signal = r.get('signal', 'HOLD')
    confidence = r.get('confidence', 0)
    signal_class = f"signal-{signal.lower()}"

    # Signal Banner
    st.markdown(f"""
    <div style="padding:20px; border-radius:12px; margin:15px 0; text-align:center;" class="{signal_class}">
        <div style="font-size:0.9em; letter-spacing:4px; opacity:0.7;">BLACK WOLF SIGNAL</div>
        <div style="font-size:3em; font-weight:900; margin:10px 0;">{signal}</div>
        <div style="font-size:1.3em;">Confidence: {confidence}%</div>
    </div>
    """, unsafe_allow_html=True)

    # Trading Levels
    entry = r.get('entry', 0)
    sl = r.get('stop_loss', 0)
    tp1 = r.get('take_profit_1', 0)
    tp2 = r.get('take_profit_2', 0)

    if entry and sl:
        risk = abs(entry - sl)
        reward1 = abs(tp1 - entry) if tp1 else 0
        rr = f"1:{reward1/risk:.1f}" if risk > 0 else "N/A"

        m1, m2, m3, m4 = st.columns(4)
        m1.markdown(f"<div class='bw-metric'><div class='value'>{entry:.2f}</div><div class='label'>Entry</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='bw-metric'><div class='value'>{sl:.2f}</div><div class='label'>Stop Loss</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='bw-metric'><div class='value'>{tp1:.2f}</div><div class='label'>TP1</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='bw-metric'><div class='value'>{tp2:.2f}</div><div class='label'>TP2</div></div>", unsafe_allow_html=True)

        st.markdown(f"**Risk/Reward:** `{rr}` | **Agent Agreement:** `{r.get('agent_agreement', 'N/A')}`")

    # Reasoning
    if r.get('reasoning'):
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 🧠 Alpha Wolf Reasoning')
        st.write(r['reasoning'])
        if r.get('key_risk'):
            st.warning(f"⚠️ Key Risk: {r['key_risk']}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Individual Agent Analyses
    agent_results = r.get('agent_results', {})
    if agent_results:
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 📋 Individual Agent Analyses')
        for agent_id, info in agent_results.items():
            if agent_id == 'deepseek_decider':
                continue
            agent = AGENTS.get(agent_id, {})
            name = agent.get('name', agent_id)
            icon = agent.get('icon', '🤖')
            status = info.get('status', 'unknown')
            if status == 'ok':
                with st.expander(f"{icon} {name}"):
                    st.text(info.get('response', ''))
            else:
                st.error(f"{icon} {name}: {info.get('error', 'Failed')}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Errors
    if r.get('errors'):
        for err in r['errors']:
            st.warning(f"⚠️ {err}")


def research_tab():
    """Tab 2: Research & Self-Improvement."""
    st.markdown('<div class="bw-card"><h2 style="color:#00f0ff;">🔬 Research & Self-Improvement</h2><p style="color:#666;">Track predictions, review outcomes, and let the wolves learn</p></div>', unsafe_allow_html=True)

    stats = get_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='bw-metric'><div class='value'>{stats['total']}</div><div class='label'>Total</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='bw-metric'><div class='value'>{stats['buy']}</div><div class='label'>Buy Signals</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='bw-metric'><div class='value'>{stats['sell']}</div><div class='label'>Sell Signals</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='bw-metric'><div class='value'>{stats['reviewed']}</div><div class='label'>Reviewed</div></div>", unsafe_allow_html=True)

    # History table
    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 📊 Analysis History')
    history = get_analysis_history(30)
    if history:
        rows = []
        for h in history:
            rows.append({
                "Time": h["timestamp"],
                "Signal": h["signal"],
                "Entry": f"{h['entry']:.2f}" if h['entry'] else "-",
                "SL": f"{h['stop_loss']:.2f}" if h['stop_loss'] else "-",
                "TP1": f"{h['take_profit_1']:.2f}" if h['take_profit_1'] else "-",
                "Conf": f"{h['confidence']}%",
                "Outcome": h.get('actual_outcome', 'Pending'),
                "Pips": f"{h['outcome_pips']:+.1f}" if h.get('outcome_pips') else "-",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No analyses yet. Run your first analysis in the Live Analysis tab.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Review section
    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### ✅ Review Past Prediction')
    if history and any(h['actual_outcome'] is None or h['actual_outcome'] == 'Pending' for h in history):
        unreviewed = [h for h in history if h['actual_outcome'] is None or h['actual_outcome'] == 'Pending']
        selected = st.selectbox(
            "Select analysis to review",
            options=range(len(unreviewed)),
            format_func=lambda i: f"{unreviewed[i]['timestamp']} - {unreviewed[i]['signal']} @ {unreviewed[i]['entry']:.2f}",
        )
        if selected is not None and selected < len(unreviewed):
            h = unreviewed[selected]
            col_a, col_b = st.columns(2)
            actual_price = col_a.number_input("Actual Price Now", value=h['entry'], step=0.01, format="%.2f", key="review_price")
            if col_b.button("✅ Submit Review", use_container_width=True):
                review = run_research_review(h['id'], actual_price)
                st.success(f"Recorded: {review['outcome']} ({review['pips']:+.1f} pips)")
                st.rerun()
    else:
        st.info("All analyses reviewed or no history.")
    st.markdown('</div>', unsafe_allow_html=True)


def settings_tab():
    """Tab 3: Settings."""
    st.markdown('<div class="bw-card"><h2 style="color:#00f0ff;">⚙️ Settings</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 🔑 API Keys')
    st.caption("Keys are set via environment variables for security.")
    st.code("""DEEPSEEK_KEY=sk-...
MISTRAL_KEY=...
HF_KEY=hf-...""", language="bash")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 🐺 About Black Wolf')
    st.markdown('''
**Black Wolf** is a Multi-Agent AI Trading System for XAU/USD.

- **5 AI Agents** analyze gold simultaneously
- **SMC (Smart Money Concepts)** analysis approach
- **Self-improvement** through outcome tracking
- **Entry on M5, Analysis on H1+**

*Built for professional gold trading.*
''')
    st.markdown('</div>', unsafe_allow_html=True)


# ── Main Tabs ──
tab1, tab2, tab3 = st.tabs(["🐺 Live Analysis", "🔬 Research", "⚙️ Settings"])

with tab1:
    manual_analysis()
with tab2:
    research_tab()
with tab3:
    settings_tab()
