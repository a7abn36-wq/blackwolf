"""Black Wolf - Multi-Agent AI Trading System
Professional Gold (XAU/USD) Analysis Platform"""

import streamlit as st
import json
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from io import StringIO
import urllib.request

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
    test_connectivity,
)

# ── Constants ──
GITHUB_RAW_URL = "https://raw.githubusercontent.com/a7abn36-wq/blackwolf/main/ea_status.json"
GITHUB_API_URL = "https://api.github.com/repos/a7abn36-wq/blackwolf/contents/ea_status.json"

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
.signal-error {
    background: linear-gradient(135deg, rgba(255, 80, 80, 0.15), rgba(180, 0, 0, 0.1));
    border: 2px solid rgba(255, 80, 80, 0.6);
    color: #ff5050;
}
.signal-none {
    background: linear-gradient(135deg, rgba(100, 100, 100, 0.15), rgba(60, 60, 60, 0.1));
    border: 2px solid rgba(100, 100, 100, 0.6);
    color: #888;
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

/* ── Status Indicator ── */
.status-online {
    color: #00ff88;
    text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
}
.status-offline {
    color: #ff3232;
    text-shadow: 0 0 10px rgba(255, 50, 50, 0.5);
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

/* ── Drawdown bar ── */
.drawdown-bar {
    height: 24px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    overflow: hidden;
    position: relative;
}
.drawdown-fill {
    height: 100%;
    border-radius: 12px;
    transition: width 0.5s ease;
}
.drawdown-label {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 0.85em;
    font-weight: 700;
    color: #fff;
    text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}

/* ── Pulse animation ── */
@keyframes pulse-green {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0, 255, 136, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(0, 255, 136, 0); }
}
@keyframes pulse-red {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.4); }
    50% { box-shadow: 0 0 0 8px rgba(255, 50, 50, 0); }
}
.pulse-green { animation: pulse-green 2s infinite; }
.pulse-red { animation: pulse-red 2s infinite; }

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
    if st.button("🔍 Test API Connection", use_container_width=True, key="test_btn"):
        with st.spinner("Testing connections from this server..."):
            try:
                conn_results = test_connectivity()
                st.session_state['conn_test'] = conn_results
            except Exception as e:
                st.session_state['conn_test'] = {"error": str(e)}

    if 'conn_test' in st.session_state:
        cr = st.session_state['conn_test']
        if 'error' in cr:
            st.error(f"Test failed: {cr['error']}")
        else:
            gem = cr.get('gemini', {})
            if gem.get('status') == 'ok':
                st.markdown(f"**✅ Gemini: WORKING** ({gem['model']})")
            else:
                st.markdown(f"**❌ Gemini: FAILED**")
                st.caption(gem.get('error', 'Unknown error'))

            cer = cr.get('cerebras', {})
            if cer.get('status') == 'ok':
                st.markdown(f"**✅ Cerebras: WORKING** ({cer['model']})")
            else:
                st.markdown(f"**❌ Cerebras: FAILED**")
                st.caption(cer.get('error', 'Unknown error'))

            if not any(v.get('status') == 'ok' for v in cr.values()):
                st.error("⚠️ No API provider is working! App cannot analyze.")
    else:
        st.caption("Click 'Test API Connection' to verify which providers work from this server.")

    st.markdown("---")
    st.markdown("**Pipeline:** Gemini 3.6 Flash → Cerebras Fallback")

    st.markdown("---")
    for aid, agent in AGENTS.items():
        st.markdown(f"**{agent['icon']} {agent['name']}**\n{agent['role']}")

with st.sidebar.expander("📊 Quick Stats"):
    stats = get_stats()
    st.metric("Total Analyses", stats["total"])
    st.metric("Avg Confidence", f"{stats['avg_confidence']}%")
    c1, c2 = st.sidebar.columns(2)
    c1.metric("BUY", stats["buy"])
    c2.metric("SELL", stats["sell"])


# ── EA Status Fetcher ──
def fetch_ea_status():
    """Fetch EA status from GitHub repo file."""
    try:
        url = GITHUB_RAW_URL + "?t=" + str(int(time.time()))
        req = urllib.request.Request(url, headers={'User-Agent': 'BlackWolfApp'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def parse_ea_time(time_str):
    """Parse EA timestamp like '2025.08.24 15:30:00' or '2025-08-24 15:30:00' to datetime."""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(time_str, fmt)
        except:
            continue
    return None


def get_ea_online_status(ea_data):
    """Determine if EA is online based on last_update or timestamp."""
    # EA sends 'timestamp', website also accepts 'last_update'
    last_update = ea_data.get('last_update', '') or ea_data.get('timestamp', '')
    # EA sends 'ONLINE' (uppercase), accept both
    status_val = ea_data.get('status', '').lower()
    if not last_update or status_val != 'online':
        return False, "Never connected"
    
    try:
        last_time = parse_ea_time(last_update)
        if last_time is None:
            return False, "Invalid timestamp"
        
        now = datetime.utcnow()
        diff = (now - last_time).total_seconds()
        
        if diff < 1200:  # 20 minutes (15 min interval + 5 min buffer)
            return True, f"Last update: {int(diff/60)} min ago"
        elif diff < 3600:
            return False, f"Stale ({int(diff/60)} min ago)"
        else:
            return False, f"Offline ({int(diff/3600)}h ago)"
    except:
        return False, "Parse error"


# ── EA Monitor Tab ──
def ea_monitor_tab():
    """Tab 4: EA Monitor - Live status from MT5 Expert Advisor."""
    
    # Auto-refresh control
    auto_refresh = st.toggle("🔄 Auto Refresh (30s)", value=True, key="ea_auto_refresh")
    
    if auto_refresh and 'ea_last_fetch' not in st.session_state:
        st.session_state['ea_last_fetch'] = 0
    
    if auto_refresh:
        now = time.time()
        if now - st.session_state.get('ea_last_fetch', 0) > 30:
            st.session_state['ea_last_fetch'] = now
            st.rerun()
    
    # Manual refresh
    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh Now", use_container_width=True):
            st.rerun()
    with col_info:
        st.caption("Data synced via GitHub. EA pushes every 15 min.")
    
    st.markdown("---")
    
    # Fetch status
    ea_data = fetch_ea_status()
    is_online, status_text = get_ea_online_status(ea_data)
    
    # ── Connection Status Banner ──
    if is_online:
        pulse_class = "pulse-green"
        status_icon = "🟢"
        status_color = "#00ff88"
        status_label = "ONLINE"
    else:
        pulse_class = "pulse-red"
        status_icon = "🔴"
        status_color = "#ff3232"
        status_label = "OFFLINE"
    
    st.markdown(f"""
    <div style="padding:16px; border-radius:12px; margin:10px 0; text-align:center; border: 2px solid {status_color}; background: rgba(0,0,0,0.3);">
        <div style="display:flex; align-items:center; justify-content:center; gap:12px;">
            <div class="{pulse_class}" style="width:16px; height:16px; border-radius:50%; background:{status_color};"></div>
            <div>
                <div style="font-size:0.85em; letter-spacing:4px; opacity:0.7;">EXPERT ADVISOR STATUS</div>
                <div style="font-size:2.2em; font-weight:900; color:{status_color};">{status_icon} {status_label}</div>
                <div style="font-size:0.95em; color:#888; margin-top:4px;">{status_text}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not is_online and ea_data.get('status') == 'offline':
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### ⚠️ EA Not Connected')
        st.markdown('''
The Expert Advisor is not reporting status. Make sure:
1. **EA is running** on MT5 XAUUSD M5 chart
2. **GitHub Token** is set in EA settings (`InpGitHubToken`)
3. **Allow WebRequest** includes `https://api.github.com`
4. **Allow Algorithmic Trading** is checked in MT5
        ''')
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    if ea_data.get('error'):
        st.warning(f"Connection error: {ea_data['error']}")
        return
    
    # ── Account Metrics Row ──
    balance = ea_data.get('account_balance', 0)
    equity = ea_data.get('account_equity', 0)
    margin = ea_data.get('margin', 0)
    free_margin = ea_data.get('free_margin', 0)
    open_trades = ea_data.get('open_trades', 0)
    total_profit = ea_data.get('total_profit', 0)
    drawdown = ea_data.get('drawdown_pct', 0)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"<div class='bw-metric'><div class='value'>{balance:,.2f}</div><div class='label'>Balance ($)</div></div>", unsafe_allow_html=True)
    m2.markdown(f"<div class='bw-metric'><div class='value'>{equity:,.2f}</div><div class='label'>Equity ($)</div></div>", unsafe_allow_html=True)
    m3.markdown(f"<div class='bw-metric'><div class='value'>{margin:,.2f}</div><div class='label'>Margin ($)</div></div>", unsafe_allow_html=True)
    m4.markdown(f"<div class='bw-metric'><div class='value'>{free_margin:,.2f}</div><div class='label'>Free Margin ($)</div></div>", unsafe_allow_html=True)
    
    m5, m6, m7, m8 = st.columns(4)
    m5.markdown(f"<div class='bw-metric'><div class='value'>{open_trades}</div><div class='label'>Open Trades</div></div>", unsafe_allow_html=True)
    
    profit_color = "#00ff88" if total_profit >= 0 else "#ff3232"
    m6.markdown(f"<div class='bw-metric'><div class='value' style='color:{profit_color}'>{total_profit:+,.2f}</div><div class='label'>Total Profit ($)</div></div>", unsafe_allow_html=True)
    
    dd_color = "#00ff88" if drawdown < 5 else ("#ffc800" if drawdown < 15 else "#ff3232")
    m7.markdown(f"<div class='bw-metric'><div class='value' style='color:{dd_color}'>{drawdown:.1f}%</div><div class='label'>Drawdown</div></div>", unsafe_allow_html=True)
    
    symbol = ea_data.get('symbol', 'N/A')
    m8.markdown(f"<div class='bw-metric'><div class='value' style='font-size:1.3em;'>{symbol}</div><div class='label'>Symbol</div></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── Drawdown Bar ──
    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 📉 Drawdown Gauge')
    dd_pct = min(drawdown, 100)
    if dd_pct < 5:
        bar_color = "linear-gradient(90deg, #00ff88, #00cc66)"
    elif dd_pct < 15:
        bar_color = "linear-gradient(90deg, #ffc800, #ff9900)"
    else:
        bar_color = "linear-gradient(90deg, #ff3232, #cc0000)"
    
    st.markdown(f"""
    <div class="drawdown-bar">
        <div class="drawdown-fill" style="width:{dd_pct}%; background:{bar_color};"></div>
        <div class="drawdown-label">{drawdown:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ── Last Signal + Reasoning ──
    last_signal = ea_data.get('last_signal', 'NONE')
    last_conf = ea_data.get('last_confidence', 0)
    last_reason = ea_data.get('last_reasoning', '')
    last_analysis = ea_data.get('last_analysis', '')
    
    signal_class_map = {
        'BUY': 'signal-buy', 'SELL': 'signal-sell',
        'HOLD': 'signal-hold', 'ERROR': 'signal-error'
    }
    sig_class = signal_class_map.get(last_signal, 'signal-none')
    
    st.markdown(f"""
    <div style="padding:16px; border-radius:12px; margin:10px 0; text-align:center;" class="{sig_class}">
        <div style="font-size:0.85em; letter-spacing:4px; opacity:0.7;">LAST EA SIGNAL</div>
        <div style="font-size:2.5em; font-weight:900; margin:8px 0;">{last_signal}</div>
        <div style="font-size:1.2em;">Confidence: {last_conf}%</div>
        {f'<div style="font-size:0.85em; margin-top:8px; opacity:0.8;">Last Analysis: {last_analysis}</div>' if last_analysis else ''}
    </div>
    """, unsafe_allow_html=True)
    
    if last_reason:
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 🧠 EA Analysis Reasoning')
        st.write(last_reason)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ── Open Positions Table ──
    open_positions = ea_data.get('open_positions', [])
    if open_positions:
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown(f'#### 📋 Open Positions ({len(open_positions)})')
        
        pos_rows = []
        for p in open_positions:
            profit = p.get('profit', 0)
            profit_str = f"{profit:+.2f}"
            pos_type = p.get('type', 'N/A')
            pos_rows.append({
                "Ticket": p.get('ticket', '-'),
                "Type": f"{'🟢' if pos_type == 'BUY' else '🔴'} {pos_type}",
                "Volume": p.get('volume', 0),
                "Open Price": f"{p.get('open_price', 0):.2f}",
                "SL": f"{p.get('sl', 0):.2f}",
                "TP": f"{p.get('tp', 0):.2f}",
                "Profit ($)": profit_str,
            })
        
        st.dataframe(pos_rows, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 📋 Open Positions')
        st.info('No open positions currently.')
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ── Equity Curve Chart ──
    equity_curve_str = ea_data.get('equity_curve', '')
    if equity_curve_str:
        try:
            curve_values = [float(x.strip()) for x in equity_curve_str.split(',') if x.strip()]
            if len(curve_values) >= 2:
                st.markdown('<div class="bw-card">', unsafe_allow_html=True)
                st.markdown(f'#### 📈 Equity Curve (last {len(curve_values)} points)')
                
                df_curve = pd.DataFrame({
                    'Point': range(len(curve_values)),
                    'Equity': curve_values
                })
                
                st.line_chart(df_curve, x='Point', y='Equity', 
                             use_container_width=True, height=300)
                
                # Show min/max
                min_eq = min(curve_values)
                max_eq = max(curve_values)
                current_eq = curve_values[-1]
                eq_change = current_eq - curve_values[0]
                change_pct = (eq_change / curve_values[0] * 100) if curve_values[0] != 0 else 0
                change_color = "#00ff88" if eq_change >= 0 else "#ff3232"
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current", f"${current_eq:,.2f}")
                c2.metric("High", f"${max_eq:,.2f}")
                c3.metric("Low", f"${min_eq:,.2f}")
                c4.metric("Period Change", f"{change_pct:+.2f}%")
                
                st.markdown('</div>', unsafe_allow_html=True)
        except Exception:
            pass
    else:
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 📈 Equity Curve')
        st.info('Equity curve will appear after the EA completes a few analysis cycles (15 min each).')
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ── Raw JSON (expandable) ──
    with st.expander("🔧 Raw EA Data (JSON)"):
        st.json(ea_data)


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

                st.session_state['last_analysis'] = result

            except Exception as e:
                st.error(f"Analysis failed: {e}")
                return

    if 'last_analysis' in st.session_state:
        r = st.session_state['last_analysis']
        display_analysis_results(r)


def display_analysis_results(r):
    """Render the analysis results beautifully."""
    signal = r.get('signal', 'HOLD')
    confidence = r.get('confidence', 0)
    signal_class = f"signal-{signal.lower()}"

    st.markdown(f"""
    <div style="padding:20px; border-radius:12px; margin:15px 0; text-align:center;" class="{signal_class}">
        <div style="font-size:0.9em; letter-spacing:4px; opacity:0.7;">BLACK WOLF SIGNAL</div>
        <div style="font-size:3em; font-weight:900; margin:10px 0;">{signal}</div>
        <div style="font-size:1.3em;">Confidence: {confidence}%</div>
    </div>
    """, unsafe_allow_html=True)

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

    if r.get('reasoning'):
        st.markdown('<div class="bw-card">', unsafe_allow_html=True)
        st.markdown('#### 🧠 Alpha Wolf Reasoning')
        st.write(r['reasoning'])
        if r.get('key_risk'):
            st.warning(f"⚠️ Key Risk: {r['key_risk']}")
        st.markdown('</div>', unsafe_allow_html=True)

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
    st.caption("Keys are embedded in agents.py (split for security).")
    st.code("Primary: Google Gemini 3.6 Flash (FREE)\nFallback: Cerebras llama-3.3-70b (FREE)", language="bash")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 🔗 EA Connection Setup')
    st.markdown('''
**To connect your MT5 Expert Advisor to this dashboard:**

1. Open EA settings in MT5 (double-click EA on chart or F7)
2. Set **InpGitHubToken** to your GitHub Personal Access Token
3. Make sure **Allow WebRequest** includes:
   - `https://generativelanguage.googleapis.com`
   - `https://api.github.com`
4. The EA will push status every 15 minutes
5. This dashboard auto-refreshes every 30 seconds

**Data flow:** EA → GitHub Repo File → Streamlit Dashboard
        ''')
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="bw-card">', unsafe_allow_html=True)
    st.markdown('#### 🐺 About Black Wolf')
    st.markdown('''
**Black Wolf** is a Multi-Agent AI Trading System for XAU/USD.

- **5 AI Agents** analyze gold simultaneously
- **SMC (Smart Money Concepts)** analysis approach
- **Self-improvement** through outcome tracking
- **Entry on M5, Analysis on H1+**
- **100% Free** - Gemini + Cerebras APIs
- **MT5 EA** for fully automatic trading
- **Live monitoring** via GitHub sync

*Built for professional gold trading.*
''')
    st.markdown('</div>', unsafe_allow_html=True)


# ── Main Tabs ──
tab1, tab2, tab3, tab4 = st.tabs(["🐺 Live Analysis", "🔬 Research", "⚙️ Settings", "📡 EA Monitor"])

with tab1:
    manual_analysis()
with tab2:
    research_tab()
with tab3:
    settings_tab()
with tab4:
    ea_monitor_tab()