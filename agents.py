"""Black Wolf - Multi-Agent AI Trading System
5 AI Agents analyze gold using SMC + Fundamental + Sentiment approach.
"""

import requests
import json
import time
import sqlite3
import os
from datetime import datetime

# ── API Keys (set via environment variables on hosting) ──
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_KEY", "")
MISTRAL_KEY = os.environ.get("MISTRAL_KEY", "")
HF_KEY = os.environ.get("HF_KEY", "")

# ── Agent Definitions ──
AGENTS = {
    "deepseek_analyst": {
        "name": "Wolf Technical (DeepSeek V3)",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "role": "SMC Technical Analyst",
        "icon": "🐺",
    },
    "mistral_risk": {
        "name": "Wolf Risk (Mistral)",
        "provider": "mistral",
        "model": "mistral-small-latest",
        "role": "Risk Manager",
        "icon": "🛡️",
    },
    "hf_llama": {
        "name": "Wolf Market (Llama 3.3 70B)",
        "provider": "huggingface",
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "role": "Market Analyst",
        "icon": "📊",
    },
    "hf_qwen": {
        "name": "Wolf Macro (Qwen 2.5 72B)",
        "provider": "huggingface",
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "role": "Macro & Geopolitical Analyst",
        "icon": "🌍",
    },
    "deepseek_decider": {
        "name": "Alpha Wolf (DeepSeek R1)",
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "role": "Final Decision Maker",
        "icon": "👑",
    },
}


# ── API Call Functions ──

def call_deepseek(model, messages, max_tokens=2000):
    """Call DeepSeek API."""
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=120,
    )
    if resp.status_code != 200:
        raise Exception(f"DeepSeek {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def call_mistral(model, messages, max_tokens=2000):
    """Call Mistral API."""
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {MISTRAL_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=120,
    )
    if resp.status_code != 200:
        raise Exception(f"Mistral {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def call_huggingface(model, messages, max_tokens=2000):
    """Call HuggingFace Inference API."""
    resp = requests.post(
        f"https://api-inference.huggingface.co/models/{model}/v1/chat/completions",
        headers={"Authorization": f"Bearer {HF_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=120,
    )
    if resp.status_code != 200:
        raise Exception(f"HuggingFace {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


PROVIDERS = {
    "deepseek": call_deepseek,
    "mistral": call_mistral,
    "huggingface": call_huggingface,
}


def call_agent(agent_id, messages):
    """Call a specific agent by ID."""
    agent = AGENTS[agent_id]
    provider_fn = PROVIDERS[agent["provider"]]
    return provider_fn(agent["model"], messages)


# ── Prompt Templates ──

TECHNICAL_PROMPT = """You are an elite SMC (Smart Money Concepts) technical analyst specializing in XAU/USD (Gold).

Your analysis focuses on:
1. **Order Blocks** - Identify major bullish/bearish order blocks from the candle data
2. **Liquidity Pools** - Where are stop losses clustered? (Above swing highs, below swing lows)
3. **Liquidity Targets** - Where is price likely to sweep liquidity?
4. **BOS (Break of Structure)** - Has structure broken? Which direction?
5. **CHoCH (Change of Character)** - First sign of trend reversal?
6. **FVG (Fair Value Gaps)** - Any imbalances price may revisit?
7. **Supply & Demand Zones** - Key institutional levels

You think like an institutional trader, NOT a retail trader using RSI/MACD.

IMPORTANT: Analyze the RAW CANDLE DATA provided. Identify patterns, order blocks, and liquidity from the actual price action.

Respond in this EXACT format:
```
MARKET_STRUCTURE: [Bullish/Bearish/Range]
TREND: [Uptrend/Downtrend/Sideways]
KEY_ORDER_BLOCKS:
- Bullish OB: [price level] - [reason]
- Bearish OB: [price level] - [reason]
LIQUIDITY_POOLS:
- Buy-side liquidity: [level] (stops above)
- Sell-side liquidity: [level] (stops below)
NEXT_MOVE: [Likely sweeps liquidity at X, then...]
BIAS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [1-100]
ANALYSIS: [2-3 sentences of SMC reasoning]
```"""

RISK_PROMPT = """You are a professional Risk Manager for a gold trading desk.

Your job is to evaluate the risk/reward of a potential trade and provide:
1. Risk assessment of the current setup
2. Optimal stop loss placement (based on structure, not arbitrary pips)
3. Take profit targets (based on liquidity targets)
4. Position sizing recommendation
5. Overall risk score

Consider:
- Current volatility (ATR-based)
- Distance to key levels (support/resistance/order blocks)
- Risk/Reward ratio (minimum 1:2 required)
- Maximum drawdown risk
- Correlation with broader market (DXY, yields)

Respond in this EXACT format:
```
RISK_LEVEL: [LOW/MEDIUM/HIGH/EXTREME]
STOP_LOSS: [price]
TAKE_PROFIT_1: [price]
TAKE_PROFIT_2: [price]
RISK_REWARD: [ratio e.g. 1:2.5]
POSITION_SIZE: [% of capital]
REASONING: [1-2 sentences explaining risk assessment]
```"""

MARKET_PROMPT = """You are a senior market analyst covering gold (XAU/USD).

Analyze the provided market data considering:
1. Overall market sentiment (risk-on vs risk-off)
2. Price action patterns (not traditional indicators)
3. Volume and momentum (from the raw data)
4. Key price levels and recent price behavior
5. How the market is likely to react at current levels

Think about what the "smart money" is doing. Where are institutions positioned?

Respond in this EXACT format:
```
SENTIMENT: [RISK-ON/RISK-OFF/MIXED]
MOMENTUM: [STRONG_UP/STRONG_DOWN/WEAK/NEUTRAL]
SMART_MONEY: [Accumulating/Distributing/Neutral]
KEY_LEVEL: [Most important price level right now]
SCENARIO_1: [Most likely scenario - what happens next]
SCENARIO_2: [Alternative scenario]
BIAS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [1-100]
ANALYSIS: [2-3 sentences]
```"""

MACRO_PROMPT = """You are a macroeconomic and geopolitical analyst specializing in gold.

You have deep knowledge of:
- Central bank policies (Fed, ECB, BOJ, PBOC)
- Geopolitical tensions and their impact on gold
- US Dollar dynamics (DXY)
- Inflation trends and their effect on gold
- Historical patterns of gold during similar market conditions
- Seasonal patterns in gold demand (China/India)
- Bond yields and real interest rates

Given the current date and market conditions, analyze:
1. What macro factors are driving gold RIGHT NOW?
2. What geopolitical risks exist?
3. What is the likely Fed policy direction?
4. How does the dollar outlook affect gold?
5. What does history tell us about similar conditions?

Respond in this EXACT format:
```
MACRO_BIAS: [BULLISH/BEARISH/NEUTRAL]
KEY_DRIVER: [Main factor driving gold right now]
RISK_EVENTS: [Upcoming events that could move gold]
HISTORICAL_PARALLEL: [Similar past situation and outcome]
GEOPOLITICAL: [Current geopolitical impact on gold]
BIAS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [1-100]
ANALYSIS: [2-3 sentences]
```"""

DECIDER_PROMPT = """You are the Alpha Wolf - the final decision maker for Black Wolf trading system.

You receive analyses from 4 specialized agents:
- 🐺 SMC Technical Analyst
- 🛡️ Risk Manager  
- 📊 Market Analyst
- 🌍 Macro/Geopolitical Analyst

Your job:
1. Weigh each agent's opinion based on their expertise
2. Identify if agents agree or disagree
3. If they disagree, use your superior reasoning to decide
4. Consider the consensus and confidence levels
5. Make the FINAL trading decision

CRITICAL RULES:
- If confidence < 60%, output HOLD
- Always provide entry, stop loss, and take profit
- Stop loss MUST be based on market structure (order blocks, swing points)
- Take profit should target liquidity pools
- Consider the risk manager's input heavily for SL/TP placement

Respond in this EXACT JSON format only (no markdown, no extra text):
{
  "signal": "BUY" or "SELL" or "HOLD",
  "entry": 0000.00,
  "stop_loss": 0000.00,
  "take_profit_1": 0000.00,
  "take_profit_2": 0000.00,
  "confidence": 75,
  "reasoning": "Summary of why this decision was made",
  "agent_agreement": "3/4 agents agree on bullish bias",
  "key_risk": "Main risk to this trade"
}"""


# ── Database ──

def get_db():
    db_path = os.environ.get("DB_PATH", "/home/z/my-project/blackwolf/blackwolf.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT DEFAULT 'XAUUSD',
            timeframe TEXT DEFAULT 'M5',
            current_price REAL,
            signal TEXT,
            entry REAL,
            stop_loss REAL,
            take_profit_1 REAL,
            take_profit_2 REAL,
            confidence INTEGER,
            reasoning TEXT,
            agent_agreement TEXT,
            key_risk TEXT,
            technical_analysis TEXT,
            risk_analysis TEXT,
            market_analysis TEXT,
            macro_analysis TEXT,
            decider_analysis TEXT,
            status TEXT DEFAULT 'pending',
            actual_outcome TEXT,
            outcome_pips REAL,
            reviewed INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS agent_performance (
            agent_id TEXT PRIMARY KEY,
            total_predictions INTEGER DEFAULT 0,
            correct_predictions INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0.0,
            last_review TEXT
        );
    """)
    conn.commit()
    conn.close()


def save_analysis(data):
    conn = get_db()
    conn.execute("""
        INSERT INTO analyses (timestamp, symbol, timeframe, current_price, signal, entry,
            stop_loss, take_profit_1, take_profit_2, confidence, reasoning, agent_agreement,
            key_risk, technical_analysis, risk_analysis, market_analysis, macro_analysis, decider_analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["timestamp"], data["symbol"], data["timeframe"], data["current_price"],
        data["signal"], data["entry"], data["stop_loss"], data["take_profit_1"],
        data["take_profit_2"], data["confidence"], data["reasoning"], data["agent_agreement"],
        data["key_risk"], data.get("technical_analysis", ""), data.get("risk_analysis", ""),
        data.get("market_analysis", ""), data.get("macro_analysis", ""), data.get("decider_analysis", ""),
    ))
    conn.commit()
    conn.close()


# ── Market Data Formatting ──

def format_market_data(candles, current_price=None, period_high=None, period_low=None):
    """Format candle data into a clear text prompt for agents."""
    if not candles:
        return "No candle data provided."

    lines = []
    lines.append(f"XAUUSD | Entry Timeframe: M5 | Analysis Timeframe: H1+")
    lines.append(f"Current Price: {current_price or candles[-1]['close']}")
    if period_high:
        lines.append(f"Period High: {period_high}")
    if period_low:
        lines.append(f"Period Low: {period_low}")
    lines.append("")

    lines.append("Recent Candles (most recent last, O/H/L/C/V):")
    for i, c in enumerate(candles[-50:], 1):
        lines.append(f"#{i:3d}  O:{c['open']:8.2f}  H:{c['high']:8.2f}  L:{c['low']:8.2f}  C:{c['close']:8.2f}  V:{c.get('volume', 0):6.0f}")

    return "\n".join(lines)


# ── Multi-Agent Orchestration ──

def run_full_analysis(candles, current_price=None, period_high=None, period_low=None):
    """Run the full 5-agent analysis pipeline."""
    market_text = format_market_data(candles, current_price, period_high, period_low)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    results = {}
    errors = []

    # Phase 1: Independent analysis
    phase1_agents = [
        ("deepseek_analyst", TECHNICAL_PROMPT),
        ("mistral_risk", RISK_PROMPT),
        ("hf_llama", MARKET_PROMPT),
        ("hf_qwen", MACRO_PROMPT),
    ]

    for agent_id, system_prompt in phase1_agents:
        agent = AGENTS[agent_id]
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Current date/time: {timestamp}\n\n{market_text}"},
            ]
            response = call_agent(agent_id, messages)
            results[agent_id] = {"status": "ok", "response": response}
        except Exception as e:
            results[agent_id] = {"status": "error", "error": str(e)}
            errors.append(f"{agent['name']}: {str(e)[:100]}")

    # Phase 2: Decision
    if errors and len(errors) >= 3:
        return {"success": False, "error": f"Too many agents failed: {'; '.join(errors)}"}

    agent_summaries = []
    for agent_id, system_prompt, _ in [(a, s, None) for a, s in phase1_agents]:
        if results[agent_id]["status"] == "ok":
            agent = AGENTS[agent_id]
            agent_summaries.append(f"### {agent['icon']} {agent['name']} ({agent['role']})\n{results[agent_id]['response']}")

    # Phase 3: Decider
    decider_input = f"""Here are the analyses from 4 specialized agents:\n\n{chr(10).join(agent_summaries)}\n\nCurrent gold price: {current_price or (candles[-1]['close'] if candles else 'Unknown')}\n
Make your final trading decision."""

    try:
        decider_messages = [
            {"role": "system", "content": DECIDER_PROMPT},
            {"role": "user", "content": decider_input},
        ]
        decider_response = call_agent("deepseek_decider", decider_messages)
        results["deepseek_decider"] = {"status": "ok", "response": decider_response}
    except Exception as e:
        results["deepseek_decider"] = {"status": "error", "error": str(e)}

    # Parse decision
    decision = parse_decision(decider_response if results["deepseek_decider"]["status"] == "ok" else "")
    decision["timestamp"] = timestamp
    decision["errors"] = errors
    decision["agent_results"] = results

    # Save to database
    if decision.get("signal"):
        save_analysis({
            "timestamp": timestamp,
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "current_price": current_price or (candles[-1]["close"] if candles else 0),
            **decision,
            "technical_analysis": results.get("deepseek_analyst", {}).get("response", ""),
            "risk_analysis": results.get("mistral_risk", {}).get("response", ""),
            "market_analysis": results.get("hf_llama", {}).get("response", ""),
            "macro_analysis": results.get("hf_qwen", {}).get("response", ""),
            "decider_analysis": results.get("deepseek_decider", {}).get("response", ""),
        })

    return decision


def parse_decision(text):
    """Parse the decision maker's JSON response."""
    import re
    json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
    if json_match:
        try:
            d = json.loads(json_match.group())
            return {
                "signal": d.get("signal", "HOLD"),
                "entry": float(d.get("entry", 0)),
                "stop_loss": float(d.get("stop_loss", 0)),
                "take_profit_1": float(d.get("take_profit_1", 0)),
                "take_profit_2": float(d.get("take_profit_2", 0)),
                "confidence": int(d.get("confidence", 50)),
                "reasoning": d.get("reasoning", ""),
                "agent_agreement": d.get("agent_agreement", ""),
                "key_risk": d.get("key_risk", ""),
            }
        except (json.JSONDecodeError, ValueError):
            pass
    return {"signal": "HOLD", "entry": 0, "stop_loss": 0, "take_profit_1": 0, "take_profit_2": 0, "confidence": 0, "reasoning": text, "agent_agreement": "", "key_risk": "Failed to parse decision"}


# ── Research / Self-Improvement ──

def get_analysis_history(limit=50):
    conn = get_db()
    rows = conn.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM analyses WHERE signal IS NOT NULL").fetchone()[0]
    buy = conn.execute("SELECT COUNT(*) FROM analyses WHERE signal='BUY'").fetchone()[0]
    sell = conn.execute("SELECT COUNT(*) FROM analyses WHERE signal='SELL'").fetchone()[0]
    hold = conn.execute("SELECT COUNT(*) FROM analyses WHERE signal='HOLD'").fetchone()[0]
    reviewed = conn.execute("SELECT COUNT(*) FROM analyses WHERE reviewed=1").fetchone()[0]
    avg_conf = conn.execute("SELECT AVG(confidence) FROM analyses WHERE confidence > 0").fetchone()[0]
    conn.close()
    return {"total": total, "buy": buy, "sell": sell, "hold": hold, "reviewed": reviewed, "avg_confidence": round(avg_conf or 0, 1)}


def run_research_review(analysis_id, actual_price, notes=""):
    """Review a past analysis and have agents learn from it."""
    conn = get_db()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": "Analysis not found"}

    data = dict(row)
    signal = data["signal"]
    entry = data["entry"]
    actual = float(actual_price)

    if signal == "BUY":
        pips = round(actual - entry, 2)
        outcome = "WIN" if pips > 0 else "LOSS"
    elif signal == "SELL":
        pips = round(entry - actual, 2)
        outcome = "WIN" if pips > 0 else "LOSS"
    else:
        pips = 0
        outcome = "HOLD"

    conn.execute("UPDATE analyses SET actual_outcome=?, outcome_pips=?, reviewed=1, status=? WHERE id=?",
                  (outcome, pips, 1, analysis_id))
    conn.commit()
    conn.close()

    return {"signal": signal, "entry": entry, "actual": actual, "pips": pips, "outcome": outcome}


# Init DB on import
init_db()