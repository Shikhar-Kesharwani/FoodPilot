"""
GoodFoods — AI Reservation Concierge (Extraordinary UI redesign)

A premium, conversation-first interface for the goodfoods booking agent.
- Branded hero, AI suggestion chips, glassmorphism sidebar with live KPIs
- Styled chat bubbles (user vs assistant) with fade-in animation
- Rich live "Agent activity" trace via st.status
All agent logic (conversation engine + tools) is preserved unchanged.
"""

# Basic imports
from dotenv import load_dotenv
import os
import html as _html

# Third party imports
import streamlit as st
import json

# Internal imports
from agent.conversation_engine import (
    generate_chat_completion,
    normalize_chat_response,
    execute_tool_calls,
    has_function_simulation,
)
from agent.toolkit import restaurant_tools
from agent.prompt_library import (
    restaurant_test_conversation_system_prompt,
    restaurant_test_conversation_system_prompt_w_fewshot,
    restaurant_test_conversation_system_prompt_w_fewshot_1,
)

# ---------- Logging ----------
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("goodfoods")

# ---------- Paths ----------
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
logger.info("PROJECT_DIR set to: %s", PROJECT_DIR)

# ---------- Env / key ----------
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    logger.info("OpenAI API key loaded successfully")
else:
    logger.error("OpenAI API key not found in environment variables")

logger.info("GoodFoods Reservation Assistant started")

# ---------- App config ----------
st.set_page_config(
    page_title="GoodFoods · AI Dining Concierge",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "GoodFoods — a conversational AI for discovering restaurants"
        " and booking tables across Bengaluru.",
    },
)

# ---------- Loading live data for KPIs ----------
def _load_json(name):
    try:
        with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Could not load %s: %s", name, e)
        return []

_RESTAURANTS = _load_json("restaurant_list.json")
_BOOKINGS = _load_json("bookings_list.json")

_restaurant_count = len(_RESTAURANTS)
_booking_count = len(_BOOKINGS)
_cuisine_set = set()
_total_capacity = 0
for _r in _RESTAURANTS:
    _cuisines = _r.get("cuisine") or []
    if isinstance(_cuisines, list):
        _cuisine_set.update(c.strip() for c in _cuisines if isinstance(c, str))
    _total_capacity += int(_r.get("restaurant_max_seating_capacity") or 0)
_cuisine_count = len(_cuisine_set)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --ink:#221e18;
  --ink-soft:#57503f;
  --emerald:#0f766e;
  --emerald-deep:#0a3b36;
  --emerald-light:#14b8a6;
  --gold:#d9a441;
  --gold-deep:#b9832a;
  --gold-light:#f3d489;
  --cream:#f6f1e7;
  --card:#fffdf8;
  --line:#ebe3d3;
  --muted:#8a8377;
  --shadow:0 10px 30px rgba(34,30,24,.10);
  --shadow-lg:0 22px 50px rgba(11,61,56,.35);
}

/* ---- Base ---- */
.stApp{
  background:
    radial-gradient(1100px 520px at 12% -6%, rgba(217,164,65,.16), transparent 58%),
    radial-gradient(1000px 640px at 108% 0%, rgba(15,118,110,.16), transparent 55%),
    var(--cream) !important;
  font-family:'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color:var(--ink);
}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2.2rem; max-width:1100px;}

h1,h2,h3,h4,h5{font-family:'Playfair Display', serif; color:var(--ink);}

/* ---- Scrollbar ---- */
::-webkit-scrollbar{width:10px;height:10px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#cfc4ae;border-radius:20px;border:2px solid transparent;background-clip:padding-box;}
::-webkit-scrollbar-thumb:hover{background:#b8a98c;background-clip:padding-box;}

/* ---- Hero ---- */
.gf-hero{
  position:relative; overflow:hidden; border-radius:26px;
  background:linear-gradient(135deg,#07352f 0%, #0f766e 52%, #149e8c 100%);
  padding:34px 38px 30px; color:#fffef7;
  box-shadow:var(--shadow-lg);
}
.gf-hero::before{content:''; position:absolute; top:-70%; left:-20%; width:60%; height:240%;
  background:radial-gradient(closest-side, rgba(255,255,255,.16), transparent); pointer-events:none;}
.gf-hero::after{content:''; position:absolute; right:-8%; bottom:-70%; width:55%; height:220%;
  background:radial-gradient(closest-side, rgba(217,164,65,.28), transparent); pointer-events:none;}
.gf-hero-top{position:relative; display:flex; align-items:center; justify-content:space-between; gap:14px; flex-wrap:wrap;}
.gf-brand{position:relative; display:flex; align-items:center; gap:14px;}
.gf-brandmark{width:52px;height:52px;border-radius:16px;display:flex;align-items:center;justify-content:center;
  font-size:26px; background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.25);
  box-shadow:0 8px 22px rgba(0,0,0,.22);}
.gf-brandtitle{font-family:'Playfair Display',serif; font-weight:800; font-size:30px; letter-spacing:.2px; margin:0; line-height:1;}
.gf-brandsub{font-size:11px; letter-spacing:3px; text-transform:uppercase; color:var(--gold-light); font-weight:600; margin-top:3px;}
.gf-live{display:inline-flex; align-items:center; gap:8px; font-size:12.5px; font-weight:600; color:#fff;
  background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.28); padding:7px 14px; border-radius:999px;
  backdrop-filter:blur(6px);}
.gf-live .dot{width:9px;height:9px;border-radius:50%;background:#4ade80;box-shadow:0 0 0 0 rgba(74,222,128,.6);animation:gfPulse 1.8s infinite;}
.gf-hero-title{font-family:'Playfair Display',serif; font-weight:700; font-size:40px; line-height:1.08; margin:26px 0 14px; position:relative;}
.gf-hero-title .gold{color:var(--gold-light);}
.gf-hero-tag{position:relative; font-size:16px; line-height:1.55; color:#eafffc; max-width:620px; opacity:.95;}
.gf-hero-tools{position:relative; margin-top:24px; display:flex; gap:10px; flex-wrap:wrap;}
.gf-toolpill{font-size:12.5px;color:#fffdf8;background:rgba(10,59,54,.35);border:1px solid rgba(255,255,255,.22);
  padding:7px 13px;border-radius:999px;font-weight:500;}
.gf-float{position:absolute; opacity:.5; filter:drop-shadow(0 8px 14px rgba(0,0,0,.25));
  animation:gfFloat 5.5s ease-in-out infinite; user-select:none; pointer-events:none;}
@keyframes gfFloat{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-12px) rotate(8deg)}}
@keyframes gfPulse{0%{box-shadow:0 0 0 0 rgba(74,222,128,.55);}70%{box-shadow:0 0 0 9px rgba(74,222,128,0);}100%{box-shadow:0 0 0 0 rgba(74,222,128,0);}}
</style>
"""
_CSS2 = """
<style>
/* ---- Chat bubbles ---- */
[data-testid="stChatMessage"]{ background:transparent; padding:0; animation:gfFadeIn .45s ease both;}
@keyframes gfFadeIn{from{opacity:0; transform:translateY(8px);}to{opacity:1; transform:translateY(0);}}

/* Avatar circles */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"]{
  width:38px; height:38px; border-radius:12px; display:flex; align-items:center; justify-content:center;
  font-size:19px; flex:none; margin-top:2px; box-shadow:0 4px 10px rgba(0,0,0,.12);}
[data-testid="stChatMessageAvatarAssistant"]{background:linear-gradient(135deg,#0f766e,#149e8c);}
[data-testid="stChatMessageAvatarUser"]{background:linear-gradient(135deg,#d9a441,#b9832a);}

/* Bubble body */
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"]{
  border-radius:20px; padding:16px 18px; max-width:78%; font-size:15px; line-height:1.6;}
[data-testid="stChatMessageContent"] p{margin:0 0 8px;}
[data-testid="stChatMessageContent"] p:last-child{margin-bottom:0;}
[data-testid="stChatMessageContent"] ul, [data-testid="stChatMessageContent"] ol{margin:6px 0 8px; padding-left:20px;}
[data-testid="stChatMessageContent"] code{background:#f0ecdf; border-radius:6px; padding:1px 6px; font-size:.86em; color:#0f766e;}

/* Assistant bubble (left, white card) */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"]{
  background:#fff; border:1px solid var(--line); box-shadow:var(--shadow);
  border-bottom-left-radius:6px;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){justify-content:flex-start;}

/* User bubble (right, emerald) */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){justify-content:flex-end;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]{
  background:linear-gradient(135deg,#0f766e,#149e8c); color:#fff;
  border-bottom-right-radius:6px; box-shadow:0 12px 26px rgba(15,118,110,.30);}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] a{color:#f3d489;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] *{color:#fff;}

/* ---- Chat input ---- */
[data-testid="stChatInput"]{background:#fff;border:1px solid var(--line);border-radius:18px;
  box-shadow:0 14px 34px rgba(34,30,24,.10); padding:4px 6px;}
[data-testid="stChatInput"] textarea{font-family:'Inter',sans-serif;}
[data-testid="stChatInput"] button{background:linear-gradient(135deg,#0f766e,#149e8c); color:#fff; border:none;}
[data-testid="stChatInput"] button:hover{background:linear-gradient(135deg,#0b5f59,#0f8f80); color:#fff;}
</style>
"""
_CSS3 = """
<style>
/* ---- Suggestion chips (buttons) ---- */
.stButton > button{
  border:1px solid var(--line); background:#fff; color:var(--ink); border-radius:14px;
  font-weight:600; padding:12px 14px; min-height:56px; height:auto; width:100%; text-align:left;
  box-shadow:0 6px 16px rgba(34,30,24,.06); transition:all .18s ease; line-height:1.35;}
.stButton > button:hover{transform:translateY(-2px); border-color:var(--gold); box-shadow:0 14px 26px rgba(0,0,0,.12);}
.stButton > button:focus{box-shadow:0 0 0 3px rgba(217,164,65,.35);}

/* ---- Sidebar ---- */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0e4a44 0%,#083832 100%); color:#eafffc;}
[data-testid="stSidebar"] *{color:#eafffc;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{color:#bfd8d3;}
.sb-brand{display:flex;align-items:center;gap:12px;padding:6px 0 4px;}
.sb-brandmark{width:44px;height:44px;border-radius:13px;background:rgba(255,255,255,.14);
  border:1px solid rgba(255,255,255,.22);display:flex;align-items:center;justify-content:center;font-size:22px;}
.sb-brandtitle{font-family:'Playfair Display',serif;font-weight:700;font-size:20px;margin:0;}
.sb-brandsub{font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:var(--gold-light);margin-top:2px;}
.sb-status{display:flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;
  background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);padding:8px 12px;border-radius:999px;margin:16px 0 4px;}
.sb-status .dot{width:9px;height:9px;border-radius:50%;background:#4ade80;animation:gfPulse 1.8s infinite;}
.sb-hr{border:none;border-top:1px solid rgba(255,255,255,.14);margin:18px 0;}
.sb-label{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:var(--gold-light);font-weight:700;margin:4px 0 10px;}
.sb-kpis{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.sb-kpi{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:12px 13px;}
.sb-kpi .num{font-family:'Playfair Display',serif;font-size:26px;font-weight:800;color:#fff;line-height:1;}
.sb-kpi .lbl{font-size:11.5px;color:#bcd6d1;margin-top:5px;}
.sb-kpi.wide{grid-column:1 / -1;}
.sb-steps{margin:6px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:11px;}
.sb-steps li{display:flex;gap:11px;align-items:flex-start;font-size:13px;line-height:1.45;color:#dcecea;}
.sb-stepdot{flex:none;width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,#d9a441,#b9832a);
  color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:1px;}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]{background:linear-gradient(135deg,#d9a441,#b9832a);
  border-color:#b9832a; font-weight:700; border-radius:12px; padding:10px 12px;}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover{background:linear-gradient(135deg,#e6b558,#c08a2c);}
</style>
"""
_CSS4 = """
<style>
/* ---- st.status (agent activity) ---- */
[data-testid="stStatusWidget"]{background:#fff; border:1px solid var(--line); border-radius:16px; box-shadow:var(--shadow); overflow:hidden;}
[data-testid="stStatusWidget"] summary{font-family:'Inter',sans-serif; font-weight:600;}
.st-ep{display:flex;gap:10px;align-items:flex-start;padding:9px 4px;font-size:13.5px;line-height:1.5;}
.st-ep .tag{flex:none;min-width:66px;font-size:10.5px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;
  color:#fff;border-radius:7px;text-align:center;padding:4px 8px;margin-top:1px;}
.st-ep .tag.plan{background:#6366f1;}
.st-ep .tag.tool{background:#0891b2;}
.st-ep .tag.result{background:#059669;}
.st-ep .tag.final{background:#d9a441;}
.st-ep .body{color:var(--ink-soft);}
.st-ep pre{white-space:pre-wrap;font-size:12px;background:#f5f1e6;border-radius:8px;padding:7px;margin:3px 0 0;}
/* ---- Misc ---- */
.gf-hint{background:#fff;border:1px solid var(--line);border-radius:16px;padding:13px 17px;margin:14px 0;}
.gf-hint b{color:var(--emerald);}
.gf-divider{border:none;border-top:2px solid var(--line);margin:14px 0;}
.gf-chips-label{font-family:'Playfair Display',serif;font-size:21px;font-weight:700;margin:4px 0 6px;color:var(--ink);}
.gf-chips-sub{color:var(--muted);font-size:13px;margin:-2px 0 12px;}
</style>
"""

# Inject global styles
st.markdown(_CSS, unsafe_allow_html=True)
st.markdown(_CSS2, unsafe_allow_html=True)
st.markdown(_CSS3, unsafe_allow_html=True)
st.markdown(_CSS4, unsafe_allow_html=True)
# ======================================================================
#  HELPERS
# ======================================================================
def _esc(text):
    """Escape text for safe injection into HTML."""
    return _html.escape(str(text), quote=True)

def render_hero():
    """Premium hero banner with animated decorations."""
    st.markdown(
        f"""
        <div class="gf-hero">
          <span class="gf-float" style="top:14px; right:8%; font-size:44px;">🍲</span>
          <span class="gf-float" style="bottom:12px; right:22%; font-size:34px; animation-delay:1.2s;">🥂</span>
          <span class="gf-float" style="top:26px; left:42%; font-size:26px; animation-delay:.6s; opacity:.35;">✨</span>
          <div class="gf-hero-top">
            <div class="gf-brand">
              <div class="gf-brandmark">🍽️</div>
              <div>
                <p class="gf-brandtitle">GoodFoods</p>
                <p class="gf-brandsub">AI Dining Concierge · Bengaluru</p>
              </div>
            </div>
            <span class="gf-live"><span class="dot"></span> Concierge online · 24/7</span>
          </div>
          <h1 class="gf-hero-title">Discover great tables.<br/><span class="gold">Let me handle the booking.</span></h1>
          <p class="gf-hero-tag">I help you find the perfect restaurant across Bengaluru by cuisine, location
          or vibe — then confirm your reservation in seconds. Just tell me what you're craving.</p>
          <div class="gf-hero-tools">
            <span class="gf-toolpill">🔎 Restaurant search</span>
            <span class="gf-toolpill">📅 Instant booking</span>
            <span class="gf-toolpill">🛡️ Capacity guardrails</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_chip_row():
    """Quick-action suggestion chips that trigger the agent."""
    st.markdown('<p class="gf-chips-label">Need a start?</p>', unsafe_allow_html=True)
    st.markdown('<p class="gf-chips-sub">One tap to get me moving on your request.</p>', unsafe_allow_html=True)
    chips = [
        ("🍜", "Suggest something to eat", "Recommend a great place to eat in Bangalore."),
        ("🍕", "Craving a cuisine", "Show me good Italian restaurants nearby."),
        ("🕗", "Book a table", "I want to book a table for 4 tonight at 8pm."),
        ("🌙", "Plans for tonight", "What are the best restaurants open tonight?"),
    ]
    cols = st.columns(len(chips))
    for col, (ico, title, prompt) in zip(cols, chips):
        with col:
            if st.button(f"{ico}  {title}", key=f"chip_{ico}", help=prompt, use_container_width=True):
                st.session_state["pending_prompt"] = prompt
    st.markdown('<hr class="gf-divider">', unsafe_allow_html=True)
def render_sidebar():
    """Story-telling sidebar with brand, status, live KPIs and how-it-works."""
    with st.sidebar:
        st.markdown(
            f"""
            <div class="sb-brand">
              <div class="sb-brandmark">🍽️</div>
              <div>
                <p class="sb-brandtitle">GoodFoods</p>
                <p class="sb-brandsub">AI Concierge</p>
              </div>
            </div>
            <div class="sb-status"><span class="dot"></span> Agent ready · GPT-4o</div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-hr">', unsafe_allow_html=True)
        st.markdown('<p class="sb-label">Live snapshot</p>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="sb-kpis">
              <div class="sb-kpi"><div class="num">{_restaurant_count}</div><div class="lbl">Restaurants</div></div>
              <div class="sb-kpi"><div class="num">{_booking_count}</div><div class="lbl">Bookings made</div></div>
              <div class="sb-kpi"><div class="num">{_cuisine_count}</div><div class="lbl">Cuisines</div></div>
              <div class="sb-kpi"><div class="num">{_total_capacity:,}</div><div class="lbl">Total seats</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-hr">', unsafe_allow_html=True)
        st.markdown('<p class="sb-label">How it works</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <ul class="sb-steps">
              <li><span class="sb-stepdot">1</span><span>Tell me what you're craving or where you'd like to dine.</span></li>
              <li><span class="sb-stepdot">2</span><span>I search GoodFoods venues across Bengaluru and rank your best fits.</span></li>
              <li><span class="sb-stepdot">3</span><span>I confirm the booking and hand you your reservation ID.</span></li>
            </ul>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="sb-hr">', unsafe_allow_html=True)
        if st.button("↺  Restart conversation", use_container_width=True):
            reset_conversation()
        st.caption("GoodFoods · Prototype on JSON · Streamlit, FastAPI & Agentic AI")
# ======================================================================
#  CONVERSATION STATE
# ======================================================================
system_prompt = restaurant_test_conversation_system_prompt_w_fewshot_1
welcome_message = (
    "Hello! I'm here to help with your reservation at GoodFoods in Bengaluru. "
    "Ask me for recommendations or book a table at your preferred location."
)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": welcome_message},
    ]
if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = None


def reset_conversation():
    logger.info("Conversation reset by user")
    st.session_state.messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": welcome_message},
    ]
    st.session_state["pending_prompt"] = None


AVATAR_ASSISTANT = "🍽️"
AVATAR_USER = "🙂"

def render_history():
    """Render all stored messages (minus system/tool) as styled bubbles."""
    for message in st.session_state.messages:
        role = message.get("role")
        if role in ("system", "tool"):
            continue
        if role == "assistant":
            with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
                st.markdown(message.get("content", ""))
        elif role == "user":
            with st.chat_message("user", avatar=AVATAR_USER):
                st.markdown(message.get("content", ""))


def render_agent_ep(tag_class, tag_text, body_md, placeholder):
    """Render a labelled 'agent activity' entry inside the status panel."""
    placeholder.markdown(
        f"""
<div class="st-ep"><span class="tag {tag_class}">{tag_text}</span>
<div class="body">{body_md}</div></div>
""",
        unsafe_allow_html=True,
    )
def run_agent(prompt):
    """Run the full agent turn: user msg -> model plan/tools -> answer."""
    logger.info("User input received: %s", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # User bubble
    with st.chat_message("user", avatar=AVATAR_USER):
        st.markdown(prompt)

    # Assistant turn
    with st.chat_message("assistant", avatar=AVATAR_ASSISTANT):
        answer_placeholder = st.empty()
        answer_placeholder.markdown(
            "<div style='color:#8a8377;font-size:14px'>&nbsp;💭&nbsp; thinking…</div>",
            unsafe_allow_html=True,
        )

        with st.status("GoodFoods is working on your request…", expanded=True, state="running") as trace:
            plan_ph = st.empty()
            tools_ph = st.empty()
            results_ph = st.empty()

            try:
                api_response = generate_chat_completion(
                    api_key=openai_api_key,
                    conversation_history=st.session_state.messages,
                    tools=restaurant_tools,
                    tool_calling_enabled=True,
                )
            except Exception as e:
                logger.error("API call failed: %s", e, exc_info=True)
                trace.update(label="Something went wrong — please restart.", state="error")
                st.error("An error occurred with the API call with User Message. Please restart the conversation.")
                st.stop()

            formatted_response = normalize_chat_response(api_response)
            try:
                assistant_msg = api_response.choices[0].message
            except Exception:
                assistant_msg = None

            if assistant_msg and (assistant_msg.content or "").strip():
                render_agent_ep("plan", "Plan", _esc(assistant_msg.content).replace("\n", "<br>"), plan_ph)
            if assistant_msg and assistant_msg.tool_calls:
                tool_items = []
                for tc in assistant_msg.tool_calls:
                    args = tc.function.arguments or ""
                    if isinstance(args, str) and len(args) > 400:
                        args = args[:400] + "…"
                    tool_items.append(f"▶&nbsp;<b>{_esc(tc.function.name)}</b><pre>{_esc(args)}</pre>")
                render_agent_ep("tool", "Tools", "<br>".join(tool_items), tools_ph)

            # ---- Direct assistant reply ----
            if not isinstance(formatted_response, list):
                response_content = formatted_response.get("content", "")
                if has_function_simulation(response_content):
                    logger.warning("Function simulation detected: %s", response_content[:100])
                    st.error("An error occurred with the API call with User Message. Please restart the conversation.")
                    st.stop()
                else:
                    answer_placeholder.markdown(response_content)
                    st.session_state.messages.append(formatted_response)
                    trace.update(label="Reply ready ✓", state="complete", expanded=False)
                return
# ---- Tool-call branch ----
            try:
                assistant_msg = api_response.choices[0].message
                assistant_msg_dict = {
                    "role": "assistant",
                    "content": (assistant_msg.content or "") if assistant_msg else "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in (assistant_msg.tool_calls or [])
                    ],
                }
                st.session_state.messages.append(assistant_msg_dict)
            except Exception as e:
                logger.error("Failed to append assistant tool_calls message: %s", e, exc_info=True)

            tool_messages = execute_tool_calls(formatted_response)
            st.session_state.messages.extend(tool_messages)
            logger.info("Tool execution completed with %d results", len(tool_messages))

            result_items = []
            for tm in tool_messages:
                name = tm.get("name", "tool")
                content = tm.get("content", "")
                if isinstance(content, str) and len(content) > 500:
                    content = content[:500] + "…"
                result_items.append(f"✔&nbsp;<b>{_esc(name)}</b><pre>{_esc(content)}</pre>")
            if result_items:
                render_agent_ep("result", "Results", "<br>".join(result_items), results_ph)

            try:
                updated_response = generate_chat_completion(
                    api_key=openai_api_key,
                    conversation_history=st.session_state.messages,
                    tools=restaurant_tools,
                    tool_calling_enabled=False,
                )
            except Exception as e:
                logger.error("API call failed after tool use: %s", e, exc_info=True)
                trace.update(label="Something went wrong — please restart.", state="error")
                st.error("An error occurred with the API call after Tool Use. Please restart the conversation.")
                st.stop()

            formatted_updated_response = normalize_chat_response(updated_response)
            answer_placeholder.markdown(formatted_updated_response.get("content", ""))
            st.session_state.messages.append(formatted_updated_response)
            trace.update(label="Reply ready ✓", state="complete", expanded=False)


# ======================================================================
#  PAGE
# ======================================================================
render_sidebar()
render_hero()
render_chip_row()
render_history()

# Handle a suggested-prompt triggered from a chip button
if st.session_state.get("pending_prompt"):
    _pending = st.session_state.pop("pending_prompt", None)
    if _pending:
        run_agent(_pending)

# Main chat input
if _prompt := st.chat_input("Ask about reservations or available restaurants…"):
    run_agent(_prompt)
