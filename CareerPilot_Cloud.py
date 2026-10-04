from __future__ import annotations

import html
import io
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests
import streamlit as st

# CareerPilot cloud edition — profile and application tracker stored in Supabase.
# Hosted edition stores profile and tracker records in Supabase.
#   python -m pip install streamlit requests
#   python -m streamlit run CareerPilot.py
APP_DIR = Path(__file__).resolve().parent
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", "")
STATUSES = ["Interested", "Applied", "Assessment", "Interview", "Offer", "Rejected", "Withdrawn"]
EMPLOYMENT_TYPES = ["Any", "Full-time", "Part-time", "Contract", "Temporary", "Internship", "Freelance"]
WORK_MODES = ["Any", "Onsite", "Hybrid", "Remote"]

# The browser extension is embedded in this single Python file and unpacked automatically.
# Chrome/Edge still requires a one-time explicit "Load unpacked" approval for security.
# Hosted edition: local browser extension bridge intentionally disabled.

st.set_page_config(
    page_title="CareerPilot — Career Workspace",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# UI-only refresh: visual styling does not change search, data, or application logic.
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --cp-bg:#f5f5f2; --cp-panel:#ffffff; --cp-ink:#171918; --cp-muted:#686e69; --cp-line:#e3e5df; --cp-accent:#c7f36b; --cp-accent-ink:#1c2611; --cp-dark:#151916; }
    .stApp { background:#f5f5f2 !important; color:var(--cp-ink) !important; font-family:'DM Sans',sans-serif; }
    [data-testid="stHeader"] { background:rgba(245,245,242,.92) !important; }
    [data-testid="stToolbar"] { right:1rem; }
    .main .block-container { max-width:1440px; padding-top:1.1rem; padding-bottom:3rem; padding-left:clamp(1rem,4vw,3.5rem); padding-right:clamp(1rem,4vw,3.5rem); }
    html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"] { color:var(--cp-ink) !important; }
    h1,h2,h3,h4,[data-testid="stHeading"] { color:#171918 !important; font-family:'Manrope','DM Sans',sans-serif !important; letter-spacing:-.045em; }
    h1 { font-weight:800 !important; } h2,h3 { font-weight:750 !important; }
    p,label,.stMarkdown,[data-testid="stMarkdownContainer"],[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] p { color:#353a36 !important; }
    [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p { color:#727871 !important; }
    .cp-hero { position:relative; overflow:hidden; isolation:isolate; border-radius:4px; padding:clamp(25px,4vw,52px); margin:0 0 15px; color:#fff !important; background:#151916; border:1px solid #151916; box-shadow:none; }
    .cp-hero:before { content:""; position:absolute; z-index:-1; width:330px; height:330px; right:-100px; top:-160px; border-radius:50%; border:1px solid rgba(199,243,107,.52); box-shadow:0 0 0 35px rgba(199,243,107,.06),0 0 0 75px rgba(199,243,107,.035); }
    .cp-hero:after { content:""; position:absolute; z-index:-1; inset:0; opacity:.13; background-image:linear-gradient(rgba(255,255,255,.12) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.12) 1px,transparent 1px); background-size:42px 42px; mask-image:linear-gradient(90deg,black,transparent 76%); pointer-events:none; }
    .cp-eyebrow { display:inline-flex; gap:8px; font-size:.72rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase; color:#c7f36b !important; margin-bottom:16px; }
    .cp-hero h1 { color:#f7f8f5 !important; font-size:clamp(2.8rem,6vw,5.3rem); line-height:.98; margin:0 0 18px; letter-spacing:-.075em; }
    .cp-hero p { color:#d4d8d1 !important; font-size:1.02rem; max-width:650px; margin:0; line-height:1.7; }
    .cp-hero-foot { display:flex; flex-wrap:wrap; gap:8px; margin-top:26px; }
    .cp-pill { display:inline-flex; align-items:center; gap:7px; padding:8px 12px; border-radius:3px; color:#f0f2ed !important; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.17); font-size:.75rem; font-weight:650; }
    [data-testid="stAlert"] { border-radius:4px; border:1px solid var(--cp-line); }
    [data-testid="stTabs"] { margin-top:16px; }
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:4px; padding:5px 0 0; border:0; border-bottom:1px solid #d9ddd5; background:transparent !important; border-radius:0; box-shadow:none; flex-wrap:wrap; }
    [data-testid="stTabs"] button[role="tab"] { border-radius:0; padding:13px 14px; height:auto; color:#777d76 !important; font-weight:700; border:0; border-bottom:2px solid transparent; transition:all .16s ease; }
    [data-testid="stTabs"] button[role="tab"] p,[data-testid="stTabs"] button[role="tab"] div,[data-testid="stTabs"] button[role="tab"] span { color:inherit !important; opacity:1 !important; }
    [data-testid="stTabs"] button[role="tab"]:hover { background:rgba(20,25,22,.04) !important; color:#171918 !important; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:transparent !important; color:#171918 !important; border-bottom:2px solid #171918; box-shadow:none; }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] p,[data-testid="stTabs"] button[role="tab"][aria-selected="true"] div,[data-testid="stTabs"] button[role="tab"][aria-selected="true"] span { color:#171918 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { background:#fff !important; border:1px solid #e1e4dd !important; border-radius:5px !important; box-shadow:0 4px 18px rgba(25,32,24,.035); }
    [data-testid="stMetric"] { padding:17px 18px; border:1px solid #e1e4dd; background:#fff !important; border-radius:5px; box-shadow:none; }
    [data-testid="stMetricLabel"],[data-testid="stMetricLabel"] p { color:#6c736b !important; font-weight:650; }
    [data-testid="stMetricValue"],[data-testid="stMetricValue"] div { color:#171918 !important; font-weight:800; font-family:'Manrope',sans-serif; }
    .stTextInput input,.stTextArea textarea,.stNumberInput input,[data-baseweb="select"]>div,[data-testid="stDateInput"] input { border-radius:4px !important; border:1px solid #d6dad2 !important; background:#fff !important; color:#171918 !important; min-height:44px; box-shadow:none; }
    input::placeholder,textarea::placeholder { color:#969c93 !important; opacity:1 !important; }
    [data-baseweb="select"] *,[data-baseweb="popover"] *,[data-baseweb="menu"] *,[role="listbox"] *,[role="option"] { color:#242824 !important; }
    [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"] { background:#fff !important; border:1px solid #d6dad2 !important; box-shadow:0 12px 30px rgba(0,0,0,.10); }
    [role="option"]:hover,[role="option"][aria-selected="true"] { background:#f0f4e9 !important; }
    .stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus { border-color:#6d8e35 !important; box-shadow:0 0 0 2px rgba(199,243,107,.35) !important; }
    .stTextArea textarea { min-height:110px; }
    .stButton button,.stFormSubmitButton button,[data-testid="stDownloadButton"] button { border-radius:4px; min-height:42px; font-weight:750; border:1px solid #d4d8d0; background:#fff; color:#171918; transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease; }
    .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] { background:#c7f36b !important; color:#17200f !important; border:1px solid #c7f36b; box-shadow:none; }
    .stButton button:hover,.stFormSubmitButton button:hover,[data-testid="stDownloadButton"] button:hover { border-color:#a8ce51; transform:translateY(-1px); box-shadow:0 5px 14px rgba(0,0,0,.07); }
    [data-testid="stForm"] { border:1px solid #e1e4dd; border-radius:5px; padding:18px; background:#fff !important; }
    [data-testid="stExpander"] { border-radius:5px; border:1px solid #e1e4dd; background:#fff !important; }
    [data-testid="stDataFrame"],[data-testid="stTable"] { border:1px solid #e1e4dd; border-radius:5px; overflow:hidden; }
    hr { border-color:#e1e4dd; margin:1.4rem 0; }
    a { color:#486622 !important; text-underline-offset:3px; }
    [data-testid="stFileUploader"] { background:#fafbf8; border:1px dashed #cbd1c4; border-radius:5px; padding:8px; }
    .cp-footer { margin-top:30px; padding:18px 4px 0; border-top:1px solid #dfe2da; color:#777d76 !important; font-size:.8rem; }
    @media(max-width:720px) { .main .block-container { padding-top:.7rem; } .cp-hero { padding:25px 20px; border-radius:3px; } .cp-hero h1 { font-size:2.7rem; } [data-testid="stTabs"] [data-baseweb="tab-list"] { gap:0; } [data-testid="stTabs"] button[role="tab"] { padding:10px 9px; font-size:.78rem; } [data-testid="stForm"] { padding:12px; } }
    @media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition:none !important; animation:none !important; scroll-behavior:auto !important; } }


     /* Full-workspace visual system: carry the editorial charcoal/lime design beyond the hero. */
     :root { --cp-bg:#101310; --cp-panel:#191d19; --cp-ink:#f2f3ee; --cp-muted:#a2aaa0; --cp-line:#30372e; --cp-accent:#c7f36b; --cp-accent-ink:#18200f; --cp-dark:#151916; }
     .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stMainBlockContainer"],
     [data-testid="stSidebar"], [data-testid="stBottom"], .main { background:#101310 !important; color:#f2f3ee !important; }
     [data-testid="stHeader"] { background:rgba(16,19,16,.94) !important; }
     .main .block-container { padding-top:1.3rem; }
     h1,h2,h3,h4,h5,h6,[data-testid="stHeading"], p,label,.stMarkdown,[data-testid="stMarkdownContainer"],
     [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p { color:#edf0e9 !important; }
     [data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p, small { color:#a2aaa0 !important; }
     [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stForm"], [data-testid="stExpander"],
     [data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stTable"] {
       background:#191d19 !important; border-color:#30372e !important; color:#edf0e9 !important;
     }
     [data-testid="stMetricLabel"],[data-testid="stMetricLabel"] p { color:#a2aaa0 !important; }
     [data-testid="stMetricValue"],[data-testid="stMetricValue"] div { color:#f2f3ee !important; }
     [data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom:1px solid #343b32 !important; }
     [data-testid="stTabs"] button[role="tab"] { color:#a2aaa0 !important; }
     [data-testid="stTabs"] button[role="tab"]:hover { background:#20261e !important; color:#f2f3ee !important; }
     [data-testid="stTabs"] button[role="tab"][aria-selected="true"],
     [data-testid="stTabs"] button[role="tab"][aria-selected="true"] p,
     [data-testid="stTabs"] button[role="tab"][aria-selected="true"] div,
     [data-testid="stTabs"] button[role="tab"][aria-selected="true"] span {
       color:#c7f36b !important; border-bottom-color:#c7f36b !important;
     }
     .stTextInput input,.stTextArea textarea,.stNumberInput input,[data-baseweb="select"]>div,
     [data-testid="stDateInput"] input,[data-testid="stTimeInput"] input {
       background:#111511 !important; color:#f2f3ee !important; border-color:#3b4438 !important;
     }
     input::placeholder,textarea::placeholder { color:#7f897c !important; }
     [data-baseweb="select"] *,[data-baseweb="popover"] *,[data-baseweb="menu"] *,[role="listbox"] *,[role="option"] { color:#edf0e9 !important; }
     [data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"] { background:#1b201b !important; border-color:#3b4438 !important; }
     [role="option"]:hover,[role="option"][aria-selected="true"] { background:#303a27 !important; }
     .stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus { border-color:#c7f36b !important; box-shadow:0 0 0 2px rgba(199,243,107,.16) !important; }
     .stButton button,.stFormSubmitButton button,[data-testid="stDownloadButton"] button {
       background:#20251f !important; color:#f2f3ee !important; border-color:#3a4337 !important;
     }
     .stButton button[kind="primary"],.stFormSubmitButton button[kind="primary"] {
       background:#c7f36b !important; color:#17200f !important; border-color:#c7f36b !important;
     }
     .stButton button:hover,.stFormSubmitButton button:hover,[data-testid="stDownloadButton"] button:hover {
       border-color:#c7f36b !important; box-shadow:0 5px 18px rgba(0,0,0,.22) !important;
     }
     [data-testid="stFileUploader"] { background:#151a15 !important; border-color:#46513e !important; }
     [data-testid="stAlert"] { background:#1b201b !important; border-color:#343d30 !important; color:#edf0e9 !important; }
     [data-testid="stAlert"] p { color:#edf0e9 !important; }
     hr { border-color:#30372e !important; }
     a { color:#c7f36b !important; }
     .cp-footer { border-color:#30372e !important; color:#a2aaa0 !important; }
     .cp-hero { margin-bottom:20px; box-shadow:0 18px 60px rgba(0,0,0,.18); }
     ::selection { background:#c7f36b; color:#17200f; }

    </style>
    """,
    unsafe_allow_html=True,
)


# Supabase REST helpers. The anon key is public; row ownership is enforced by RLS and the user's access token.
AUTH_BASE = f"{SUPABASE_URL}/auth/v1"
REST_BASE = f"{SUPABASE_URL}/rest/v1"
PROFILE_FIELDS = ["full_name", "email", "phone", "city", "linkedin", "portfolio", "resume_text", "education", "experience", "skills", "country", "years_experience", "notice_period", "salary_expectation", "work_authorization"]

def _headers(json_body=True):
    token = st.session_state.get("access_token", "")
    h = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token or SUPABASE_ANON_KEY}"}
    if json_body: h["Content-Type"] = "application/json"
    return h

def _api(method, path, payload=None, params=None, prefer=None):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY: raise RuntimeError("Supabase secrets are not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit secrets.")
    headers = _headers(payload is not None)
    if prefer: headers["Prefer"] = prefer
    response = requests.request(method, REST_BASE + path, headers=headers, json=payload, params=params, timeout=20)
    if not response.ok: raise RuntimeError(response.json().get("message", response.text[:300]) if response.text else f"Supabase request failed ({response.status_code})")
    return response.json() if response.text.strip() else []

def auth_request(path, payload):
    response = requests.post(AUTH_BASE + path, headers={"apikey": SUPABASE_ANON_KEY, "Content-Type":"application/json"}, json=payload, timeout=20)
    try: data=response.json()
    except Exception: data={}
    if not response.ok: raise RuntimeError(data.get("msg") or data.get("message") or data.get("error_description") or data.get("error") or f"Authentication failed ({response.status_code})")
    return data

def auth_gate():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        st.error("Supabase is not configured yet.")
        st.markdown("Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` to your Streamlit app secrets. Never use a service-role key here.")
        st.stop()
    if st.session_state.get("access_token") and st.session_state.get("user_id"):
        with st.sidebar:
            st.caption(f"Signed in as {st.session_state.get('user_email','user')}")
            if st.button("Sign out"):
                for k in ("access_token","refresh_token","user_id","user_email"): st.session_state.pop(k, None)
                st.rerun()
        return
    st.title("CareerPilot")
    st.subheader("Sign in or create your account")
    login, signup = st.tabs(["Log in", "Sign up"])
    with login:
        with st.form("cloud_login"):
            email=st.text_input("Email address", key="login_email")
            password=st.text_input("Password", type="password", key="login_password")
            submit=st.form_submit_button("Log in", type="primary")
        if submit:
            try:
                data=auth_request("/token?grant_type=password", {"email":email.strip(),"password":password})
                st.session_state.access_token=data["access_token"]; st.session_state.refresh_token=data.get("refresh_token","")
                st.session_state.user_id=data["user"]["id"]; st.session_state.user_email=data["user"].get("email",email.strip())
                st.rerun()
            except Exception as e: st.error(str(e))
    with signup:
        st.warning("Signups are limited by the database trigger to five accounts for this dedicated Supabase project. Pending email confirmations reserve a slot.")
        with st.form("cloud_signup"):
            email=st.text_input("Email address", key="signup_email")
            password=st.text_input("Password (at least 8 characters recommended)", type="password", key="signup_password")
            submit=st.form_submit_button("Create account", type="primary")
        if submit:
            if len(password)<8: st.error("Please choose a password with at least 8 characters.")
            else:
                try:
                    data=auth_request("/signup", {"email":email.strip(),"password":password})
                    if data.get("access_token") and data.get("user"):
                        st.session_state.access_token=data["access_token"]; st.session_state.refresh_token=data.get("refresh_token","")
                        st.session_state.user_id=data["user"]["id"]; st.session_state.user_email=data["user"].get("email",email.strip())
                        st.success("Account created and signed in."); st.rerun()
                    else: st.success("Signup request accepted. Check your email to confirm the account, then log in.")
                except Exception as e: st.error(str(e))
    st.stop()

def get_profile():
    rows=_api("GET", "/careerpilot_profiles", params={"select":"*","user_id":f"eq.{st.session_state.user_id}","limit":"1"})
    if rows: return rows[0]
    row={"user_id":st.session_state.user_id,"email":st.session_state.get("user_email","")}
    return _api("POST", "/careerpilot_profiles", row, prefer="return=representation")[0]

def save_profile(data):
    payload={k:str(data.get(k) or "") for k in PROFILE_FIELDS}
    payload["user_id"]=st.session_state.user_id
    payload["updated_at"]=datetime.now(timezone.utc).isoformat()
    rows=_api("GET", "/careerpilot_profiles", params={"select":"user_id","user_id":f"eq.{st.session_state.user_id}","limit":"1"})
    if rows: _api("PATCH", "/careerpilot_profiles", payload, params={"user_id":f"eq.{st.session_state.user_id}"}, prefer="return=minimal")
    else: _api("POST", "/careerpilot_profiles", payload, prefer="return=minimal")

def add_application(company, title, url="", status="Interested", applied_on="", notes=""):
    payload={"user_id":st.session_state.user_id,"company":company.strip(),"title":title.strip(),"url":url.strip(),"status":status,"applied_on":applied_on,"notes":notes.strip(),"created_at":datetime.now(timezone.utc).isoformat()}
    _api("POST", "/careerpilot_applications", payload, prefer="return=minimal")

def list_applications():
    return _api("GET", "/careerpilot_applications", params={"select":"*","order":"id.desc"})

def update_application(row_id, payload):
    _api("PATCH", "/careerpilot_applications", payload, params={"id":f"eq.{row_id}"}, prefer="return=minimal")

def delete_application(row_id):
    _api("DELETE", "/careerpilot_applications", params={"id":f"eq.{row_id}"})

def clean_text(value):
    return html.unescape(re.sub(r"<[^>]+>", " ", str(value or ""))).replace("\xa0", " ").strip()


def tokens(text):
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}", (text or "").lower()))

STOPWORDS = set("a an and are as at be been being by can could did do does for from had has have he her his how i if in into is it its may might must of on or our shall should that the their them then there these they this those to was we were what when where which who will with would you your job role work team using such about across within while per preferred required requirements responsibilities qualifications experience candidate candidates including plus also", )


def keyword_analysis(resume, jd):
    rt, jt = tokens(resume) - STOPWORDS, tokens(jd) - STOPWORDS
    matched = sorted(rt & jt)
    missing = sorted(jt - rt)
    score = round(100 * len(matched) / max(1, len(jt)))
    return score, matched, missing


def extract_sections(text):
    """Extract simple resume sections for actionable formatting checks."""
    headings = {
        "experience": r"(?im)^\s*(professional\s+experience|work\s+experience|experience|employment\s+history)\s*$",
        "education": r"(?im)^\s*(education|academic\s+background|qualifications)\s*$",
        "skills": r"(?im)^\s*(technical\s+skills|skills|core\s+competencies|key\s+skills)\s*$",
        "projects": r"(?im)^\s*(projects|academic\s+projects|key\s+projects)\s*$",
        "certifications": r"(?im)^\s*(certifications|certificates|licenses)\s*$",
        "summary": r"(?im)^\s*(professional\s+summary|summary|profile|career\s+objective)\s*$",
    }
    found = [name for name, pattern in headings.items() if re.search(pattern, text or "")]
    return found


def make_tailoring_draft(resume, jd, title="Target Role"):
    score, matched, missing = keyword_analysis(resume, jd)
    lines = [
        f"CV TAILORING WORKSHEET — {title}", "=" * 48,
        "IMPORTANT: Review and edit every statement. Do not add skills, experience, dates, metrics, or qualifications you cannot verify.",
        "", "TARGETED PROFESSIONAL SUMMARY — EDIT BEFORE USE",
        f"Candidate with experience/knowledge in {', '.join(matched[:8]) if matched else '[add your relevant verified skills]'}. "
        f"Seeking to contribute relevant strengths to the {title} role. Replace this text with a truthful summary supported by your actual experience.",
        "", "RELEVANT KEYWORDS TO CHECK AGAINST YOUR ACTUAL EXPERIENCE",
        ", ".join(matched) if matched else "No clear matching keywords detected.",
        "", "JOB-DESCRIPTION TERMS NOT DETECTED IN THE CURRENT CV",
        ", ".join(missing[:120]) if missing else "No missing terms detected by the simple comparison.",
        "", "TAILORING ACTIONS", 
        "1. Move the most relevant real experience and projects nearer the top.",
        "2. Add missing terms only when they accurately describe your skills or work.",
        "3. For each relevant role/project, use action + task + result; include numbers only when verifiable.",
        "4. Keep conventional headings, readable text, consistent dates, and simple formatting.",
        "5. Proofread the final CV and confirm every claim before submitting.",
        "", f"Keyword overlap indicator: {score}% (not an employer ATS score or pass prediction).", "",
        "--- ORIGINAL RESUME TEXT FOR EDITING ---", resume.strip(),
    ]
    return "\n".join(lines), score, matched, missing


def portal_urls(query, location, work_mode, employment_type, recency):
    """Build portal searches using query-string URLs where possible.

    Portal URL patterns change, so the broad web-search fallbacks intentionally
    target each site's indexed job pages instead of relying on fragile slugs.
    """
    raw_q = (query or "").strip()
    loc_text = (location or "India").strip() or "India"
    mode_term = {
        "Any": "", "Onsite": ' onsite OR "on-site" OR office',
        "Hybrid": " hybrid", "Remote": " remote"
    }.get(work_mode, "")
    type_term = {
        "Any": "", "Full-time": ' "full time"', "Part-time": ' "part time"',
        "Contract": " contract", "Temporary": " temporary",
        "Internship": " internship", "Freelance": " freelance"
    }.get(employment_type, "")
    search_text = " ".join(part for part in (raw_q, mode_term, type_term) if part).strip() or "jobs"
    q = quote_plus(search_text)
    loc = quote_plus(loc_text)
    days = {"Any time": None, "Past 24 hours": 1, "Past 7 days": 7,
            "Past 14 days": 14, "Past 30 days": 30}.get(recency)
    linkedin_filter = f"&f_TPR=r{days * 86400}" if days else ""
    indeed_filter = f"&fromage={days}" if days else ""
    google_filter = "" if not days else ("&tbs=qdr:d" if days == 1 else "&tbs=qdr:w" if days <= 7 else "&tbs=qdr:m")
    slug_q = re.sub(r"[^a-zA-Z0-9]+", "-", raw_q).strip("-").lower() or "jobs"
    slug_loc = re.sub(r"[^a-zA-Z0-9]+", "-", loc_text).strip("-").lower() or "india"
    google_query = quote_plus(f'{search_text} jobs {loc_text}')
    # Search common ATS-hosted company career pages directly. These are Google
    # dorks, not a claim that every employer uses one of these platforms.
    role_for_dork = f'"{raw_q}"' if raw_q else 'jobs'
    ats_sites = (
        'site:boards.greenhouse.io OR site:jobs.lever.co OR '
        'site:myworkdayjobs.com OR site:wd5.myworkdayjobs.com OR '
        'site:jobs.ashbyhq.com OR site:careers.smartrecruiters.com OR '
        'site:apply.workable.com OR site:jobs.jobvite.com'
    )
    company_dork = f'({ats_sites}) {role_for_dork} "{loc_text}"'
    if work_mode != "Any":
        company_dork += f' {mode_term}'
    if employment_type != "Any":
        company_dork += f' {type_term}'
    company_query = quote_plus(company_dork)
    remote_dork = f'({ats_sites}) {role_for_dork} (remote OR "work from home") (India OR Bengaluru OR Bangalore OR Hyderabad OR Pune OR Mumbai OR Chennai)'
    if employment_type != "Any":
        remote_dork += f' {type_term}'
    remote_query = quote_plus(remote_dork)
    shine_query = quote_plus(f'site:shine.com/job-search {search_text} {loc_text}')
    glassdoor_query = quote_plus(f'site:glassdoor.co.in/Job {search_text} {loc_text}')
    return [
        ("Naukri", f"https://www.naukri.com/{slug_q}-jobs-in-{slug_loc}"),
        ("LinkedIn Jobs", f"https://www.linkedin.com/jobs/search/?keywords={q}&location={loc}{linkedin_filter}"),
        ("Indeed India", f"https://in.indeed.com/jobs?q={q}&l={loc}{indeed_filter}"),
        ("Foundit", f"https://www.foundit.in/srp/results?query={q}&locations={loc}"),
        ("Google Jobs / web search", f"https://www.google.com/search?q={google_query}{google_filter}"),
        # Shine's search URL patterns vary; use an indexed job-search query as a resilient fallback.
        ("Shine", f"https://www.google.com/search?q={shine_query}"),
        ("TimesJobs", f"https://www.timesjobs.com/candidate/job-search.html?txtKeywords={q}&txtLocation={loc}"),
        ("Wellfound (startup jobs)", f"https://wellfound.com/jobs"),
        ("Glassdoor", f"https://www.google.com/search?q={glassdoor_query}{google_filter}"),
        ("Company career pages (ATS Google dork)", f"https://www.google.com/search?q={company_query}{google_filter}"),
        # Additional specialist portals. These links go to the portal itself,
        # not Google/site: searches. Query parameters are used where the portal
        # exposes a reasonably stable search route; otherwise open its own jobs page.
        ("Instahyre — curated tech and product roles", "https://www.instahyre.com/"),
        ("Hirist — technology jobs", f"https://www.hirist.tech/search/{quote_plus(raw_q.lower().replace(' ', '-'))}-jobs" if raw_q else "https://www.hirist.tech/"),
        ("iimjobs — management and specialist roles", f"https://www.iimjobs.com/search?search={q}&location={loc}"),
        ("Internshala — internships and entry-level roles", f"https://internshala.com/jobs/keywords-{quote_plus(raw_q.lower().replace(' ', '-'))}/" if raw_q else "https://internshala.com/jobs/"),
        ("Apna — frontline and local hiring", f"https://www.apna.co/jobs?keyword={q}&location={loc}"),
        ("WorkIndia — local and frontline roles", f"https://www.workindia.in/jobs/?keyword={q}&location={loc}"),
        ("Turing — remote technology roles", f"https://work.turing.com/jobs?search={q}" if raw_q else "https://work.turing.com/jobs"),
        ("Y Combinator Work at a Startup — startup roles", f"https://www.workatastartup.com/jobs?query={q}&location={loc}" if raw_q else "https://www.workatastartup.com/jobs"),
    ]



# Supplementary remote-job discovery. These public feeds are independent of portal search.
FEED_HEADERS = {"User-Agent": "CareerPilot/1.0 (personal job search app)"}
FEED_TIMEOUT = 15
def feed_parse_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            stamp = float(value)
            if stamp > 10_000_000_000:
                stamp /= 1000
            return datetime.fromtimestamp(stamp, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    try:
        dt = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z"):
            try:
                dt = datetime.strptime(str(value).strip(), fmt)
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
            except ValueError:
                pass
    return None


def feed_job(source, title, company, location, description, url, posted, job_type=""):
    return {
        "source": clean_text(source), "title": clean_text(title) or "Untitled role",
        "company": clean_text(company) or "Company not listed",
        "location": clean_text(location) or "Remote — location not specified",
        "description": clean_text(description), "url": clean_text(url),
        "posted_dt": feed_parse_date(posted), "job_type": clean_text(job_type),
    }


def _feed_get_json(url, params=None):
    response = requests.get(url, params=params, headers=FEED_HEADERS, timeout=FEED_TIMEOUT)
    response.raise_for_status()
    return response.json()


def fetch_remote_feed_sources(query=""):
    """Fetch independent public feeds; one source failing does not block the others."""
    all_jobs, report = [], []
    q = (query or "").strip()
    sources = []
    def remotive():
        payload = _feed_get_json("https://remotive.com/api/remote-jobs", {"limit": 500, **({"search": q[:100]} if q else {})})
        return [feed_job("Remotive", x.get("title"), x.get("company_name"), x.get("candidate_required_location") or "Remote — country eligibility not specified", x.get("description"), x.get("url"), x.get("publication_date"), x.get("job_type")) for x in payload.get("jobs", []) if isinstance(x, dict)]
    def remoteok():
        payload = _feed_get_json("https://remoteok.com/api")
        items = [x for x in payload if isinstance(x, dict) and x.get("position")] if isinstance(payload, list) else []
        if q:
            terms = [t for t in q.lower().split() if len(t) > 1]
            items = [x for x in items if all(t in (str(x.get("position", "")) + " " + str(x.get("company", "")) + " " + str(x.get("tags", "")) + " " + str(x.get("description", ""))).lower() for t in terms)]
        return [feed_job("Remote OK", x.get("position"), x.get("company"), x.get("location") or "Remote — country eligibility not specified", x.get("description"), x.get("url"), x.get("date") or x.get("epoch"), x.get("tags", [])) for x in items]
    def himalayas():
        # No country parameter: include remote roles across countries/regions.
        params = {"sort": "recent", "page": 1}
        if q: params["q"] = q[:100]
        payload = _feed_get_json("https://himalayas.app/jobs/api/search", params)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        return [feed_job("Himalayas", x.get("title"), x.get("companyName") or x.get("company"), x.get("location") or "Remote — eligibility not specified", x.get("description"), x.get("applicationLink") or x.get("url") or x.get("guid"), x.get("pubDate") or x.get("publishedAt") or x.get("createdAt"), x.get("employmentType") or x.get("employment_type")) for x in items if isinstance(x, dict)]
    def jobicy():
        # Jobicy's public API does not document "india" as a supported geo slug.
        # Request the current remote feed and apply India eligibility in CareerPilot's
        # common client-side filter, rather than sending a geo=india parameter that
        # causes HTTP 400. Jobicy supports tag searches of 3–50 characters.
        params = {"count": 100}
        if len(q) >= 3:
            params["tag"] = q[:50]
        payload = _feed_get_json("https://jobicy.com/api/v2/remote-jobs", params)
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(str(payload.get("error") or "Jobicy API returned success=false"))
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        return [feed_job("Jobicy", x.get("jobTitle") or x.get("title"), x.get("companyName") or x.get("company"), x.get("jobGeo") or x.get("location") or "Remote — eligibility not specified", x.get("jobDescription") or x.get("jobExcerpt") or x.get("description"), x.get("url") or x.get("jobUrl"), x.get("pubDate") or x.get("datePosted"), x.get("jobType") or x.get("employmentType")) for x in items if isinstance(x, dict)]
    def arbeitnow():
        payload = _feed_get_json("https://www.arbeitnow.com/api/job-board-api")
        items = payload.get("data", []) if isinstance(payload, dict) else []
        jobs = [feed_job("Arbeitnow", x.get("title"), x.get("company_name"), x.get("location"), x.get("description"), x.get("url"), x.get("created_at"), x.get("job_types", [])) for x in items if isinstance(x, dict)]
        if q:
            terms = [t for t in q.lower().split() if len(t) > 1]
            jobs = [x for x in jobs if all(t in (x['title']+' '+x['company']+' '+x['description']).lower() for t in terms)]
        return jobs
    sources = [("Himalayas (international remote)", himalayas), ("Jobicy (international remote)", jobicy), ("Remotive (international remote)", remotive), ("Remote OK (international remote)", remoteok), ("Arbeitnow (remote roles; eligibility varies)", arbeitnow)]
    for name, fn in sources:
        try:
            result = fn()
            all_jobs.extend(result)
            report.append({"Source": name, "Fetched": len(result), "Status": "OK"})
        except Exception as exc:
            report.append({"Source": name, "Fetched": 0, "Status": f"{type(exc).__name__}: {str(exc)[:150]}"})
    unique, seen = [], set()
    for job in all_jobs:
        key = job["url"].strip().rstrip("/").lower() or (job["company"].lower(), job["title"].lower())
        if key in seen: continue
        seen.add(key); unique.append(job)
    return unique, report


def feed_remote_eligibility(job):
    """Describe location eligibility without excluding any country."""
    location = (job.get("location") or "").lower()
    text = (job.get("title", "") + " " + job.get("description", "")[:2500]).lower()
    restricted_phrases = (
        "us citizens only", "u.s. citizens only", "must reside in the united states",
        "must be based in the us", "uk residents only", "must reside in the uk",
        "canada residents only", "must reside in canada", "australia residents only",
        "must reside in australia", "only applicants in the united states",
    )
    if any(term in (location + " " + text) for term in restricted_phrases):
        return "Country-restricted — check listing"
    if any(term in (location + " " + text) for term in (
        "worldwide", "work from anywhere", "open to all countries", "anywhere in the world",
        "remote worldwide", "global remote", "anywhere", "all locations"
    )):
        return "Worldwide / broad eligibility stated"
    if location.strip() and location.lower() not in ("remote", "remote — eligibility not specified", "remote — country eligibility not specified"):
        return "Location/eligibility listed — verify"
    return "Remote — eligibility not specified"


def add_application(company, title, url="", status="Interested", applied_on="", notes=""):
    payload={"user_id":st.session_state.user_id,"company":company.strip(),"title":title.strip(),"url":url.strip(),"status":status,"applied_on":applied_on,"notes":notes.strip(),"created_at":datetime.now(timezone.utc).isoformat()}
    _api("POST", "/careerpilot_applications", payload, prefer="return=minimal")


# Hosted edition disables the local-only browser autofill bridge.

auth_gate()
profile = get_profile()
st.markdown(
    """
    <section class="cp-hero">
      <div class="cp-eyebrow">✦ YOUR CAREER WORKSPACE</div>
      <h1>CareerPilot</h1>
      <p>Find opportunities, tailor your CV, prepare stronger applications, and keep your job hunt organised — all from one local workspace.</p>
      <div class="cp-hero-foot">
        <span class="cp-pill">🌐 Multi-portal search</span>
        <span class="cp-pill">🌍 Global remote roles</span>
        <span class="cp-pill">📄 CV &amp; ATS readiness</span>
        <span class="cp-pill">📌 Application tracking</span>
        <span class="cp-pill">🔒 Local-first workspace</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)
st.caption("A sharper workspace for finding roles, refining your CV, and managing every application — privately saved to your account.")

search_tab, remote_tab, cv_tab, helper_tab, profile_tab, tracker_tab = st.tabs([
    "🌐 Job Portal Search", "🌍 Remote Feed Scan", "📄 CV Optimiser & ATS", "✉️ Application Helper", "👤 My Details", "📌 Application Tracker"
])

with search_tab:
    st.subheader("Find your next opportunity")
    st.write("Choose a title, skill, company or industry; set the location and filters; then open the generated search on the portal. Use broad terms if you want to explore a whole career field.")
    col1, col2 = st.columns([2, 1])
    with col1:
        query = st.text_input("Job title / keywords / company / industry", placeholder="e.g. SOC Analyst, Accountant, Nurse, Python, Sales, Teacher", key="portal_query")
    with col2:
        location = st.text_input("Location", value=profile.get("city") or "India", placeholder="India, Bengaluru, Mumbai…", key="portal_location")
    f1, f2, f3 = st.columns(3)
    with f1:
        work_mode = st.selectbox("Work mode", WORK_MODES, key="portal_mode")
    with f2:
        employment_type = st.selectbox("Employment type", EMPLOYMENT_TYPES, key="portal_employment")
    with f3:
        recency = st.selectbox("Posted", ["Any time", "Past 24 hours", "Past 7 days", "Past 14 days", "Past 30 days"], index=2, key="portal_recency")
    if st.button("Build portal searches", type="primary", key="build_portals"):
        st.session_state["portal_results"] = portal_urls(query, location, work_mode, employment_type, recency)
        st.session_state["portal_search_summary"] = {"query": query.strip() or "All roles", "location": location.strip() or "India", "mode": work_mode, "employment": employment_type, "recency": recency}
    if st.session_state.get("portal_results"):
        summary = st.session_state.get("portal_search_summary", {})
        st.markdown("#### Search links")
        st.caption(f"Search: {summary.get('query')} · {summary.get('location')} · {summary.get('mode')} · {summary.get('employment')} · {summary.get('recency')}")
        for label, url in st.session_state["portal_results"]:
            st.markdown(f"- [{label}]({url})")
        st.caption("Filters are encoded where the portal supports them. Apna receives the search term through its keyword parameter. Instahyre relies heavily on your signed-in profile and job preferences, and does not reliably support prefilled public keyword-search URLs; open Instahyre and use its Jobs/Opportunities area. Other portals may interpret keywords differently; verify filters on the destination site.")
    st.divider()
    st.markdown("#### Add a role directly to your tracker")
    with st.form("quick_add_job"):
        qc1, qc2 = st.columns(2)
        with qc1:
            quick_company = st.text_input("Company")
            quick_title = st.text_input("Job title")
        with qc2:
            quick_url = st.text_input("Job listing URL")
            quick_status = st.selectbox("Status", STATUSES, key="quick_status")
        quick_notes = st.text_area("Notes (optional)")
        quick_submit = st.form_submit_button("Save role to tracker")
        if quick_submit:
            if not quick_company.strip() or not quick_title.strip():
                st.error("Company and job title are required.")
            else:
                add_application(quick_company, quick_title, quick_url, quick_status, "", quick_notes)
                st.success("Role saved to your application tracker.")


with remote_tab:
    st.subheader("Discover international remote roles")
    st.write("Search remote vacancies internationally across multiple public feeds. No India-only country filter is applied; some employers still restrict remote work to specific countries, so check each original listing's eligibility.")
    rf1, rf2 = st.columns([2, 1])
    with rf1:
        feed_query = st.text_input("Role / skill keywords (optional)", placeholder="e.g. customer support, developer, analyst, designer", key="feed_query")
    with rf2:
        feed_recency = st.selectbox("Published", ["Any time", "Past 24 hours", "Past 7 days", "Past 14 days", "Past 30 days"], index=2, key="feed_recency")
    feed_type = st.selectbox("Employment type", EMPLOYMENT_TYPES, key="feed_type")
    include_undated = st.checkbox("Include listings without a published date", value=True, key="feed_undated")
    if st.button("Scan remote job feeds", type="primary", key="run_remote_feed_scan"):
        with st.spinner("Fetching public job feeds. A slow source may take several seconds…"):
            jobs, report = fetch_remote_feed_sources(feed_query)
        st.session_state["remote_feed_jobs"] = jobs
        st.session_state["remote_feed_report"] = report
        st.session_state["remote_feed_query"] = feed_query
    if st.session_state.get("remote_feed_report") is not None:
        report = st.session_state.get("remote_feed_report", [])
        st.markdown("#### Source status")
        st.dataframe(report, use_container_width=True, hide_index=True)
        jobs = st.session_state.get("remote_feed_jobs", [])
        days = {"Any time": None, "Past 24 hours": 1, "Past 7 days": 7, "Past 14 days": 14, "Past 30 days": 30}[feed_recency]
        cutoff = datetime.now(timezone.utc) - timedelta(days=days) if days else None
        filtered = []
        for job in jobs:
            posted = job.get("posted_dt")
            if posted and posted > datetime.now(timezone.utc) + timedelta(days=1):
                continue
            if posted and cutoff and posted < cutoff:
                continue
            if not posted and not include_undated:
                continue
            eligibility = feed_remote_eligibility(job)
            if feed_type != "Any":
                jt = str(job.get("job_type", "")).lower().replace("-", " ")
                wanted = feed_type.lower().replace("-", " ")
                if wanted not in jt and not (feed_type == "Full-time" and "full time" in jt):
                    continue
            job["eligibility"] = eligibility
            job["posted_display"] = posted.astimezone().strftime("%d %b %Y") if posted else "Date not provided — verify source"
            filtered.append(job)
        filtered.sort(key=lambda j: -(j.get("posted_dt").timestamp() if j.get("posted_dt") else 0))
        st.metric("Listings after selected filters", len(filtered))
        if not filtered:
            st.warning("No listings matched these filters. Check source status above, broaden the keywords, or include listings without dates.")
        for idx, job in enumerate(filtered[:100]):
            with st.container(border=True):
                st.markdown(f"**{job['title']}** — {job['company']}")
                st.caption(f"Source: {job['source']} · Location: {job['location']} · Eligibility: {job['eligibility']} · Posted: {job['posted_display']} · Type: {job['job_type'] or 'Not specified'}")
                if job.get("url"):
                    st.markdown(f"[Open original listing]({job['url']})")
                if job.get("description"):
                    with st.expander("Description preview"):
                        st.markdown(job["description"][:2200], unsafe_allow_html=False)
                if st.button("Save to application tracker", key=f"save_feed_{idx}"):
                    add_application(job["company"], job["title"], job.get("url", ""), "Interested", "", f"Found via {job['source']}; eligibility: {job['eligibility']}; posted: {job['posted_display']}")
                    st.success("Saved to application tracker.")
        if len(filtered) > 100:
            st.caption(f"Showing the first 100 of {len(filtered)} matching listings.")
        st.caption("Public feeds can change, rate-limit requests, or omit fields. A successful fetch is not a guarantee the vacancy is still open; verify details on the employer's original listing.")

with cv_tab:
    st.subheader("CV optimiser & ATS readiness")
    st.caption("Local keyword and document-readiness analysis. No paid AI service is called. It does not guarantee ATS success.")
    resume_input = st.text_area("Your current CV / resume text", value=profile.get("resume_text", ""), height=280, key="cv_resume")
    jd_input = st.text_area("Full job description (JD)", height=280, placeholder="Paste the job description here…", key="cv_jd")
    target_title = st.text_input("Target job title (for the draft heading)", placeholder="e.g. Cyber Security Engineer", key="cv_target_title")
    if st.button("Analyse CV and build tailoring worksheet", type="primary", key="analyse_cv"):
        if not resume_input.strip() or not jd_input.strip():
            st.error("Paste both the current CV and the full job description.")
        else:
            draft, score, matched, missing = make_tailoring_draft(resume_input, jd_input, target_title.strip() or "Target Role")
            st.session_state["cv_analysis"] = {"draft": draft, "score": score, "matched": matched, "missing": missing, "sections": extract_sections(resume_input), "resume": resume_input, "jd": jd_input}
    analysis = st.session_state.get("cv_analysis")
    if analysis:
        score = analysis["score"]
        m1, m2, m3 = st.columns(3)
        m1.metric("Keyword overlap indicator", f"{score}%")
        m2.metric("JD terms matched", len(analysis["matched"]))
        m3.metric("JD terms not detected", len(analysis["missing"]))
        st.caption("This is a basic word-overlap estimate, not a real ATS score. It does not assess employer-specific parsing, ranking, experience quality, or eligibility.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Terms found in both CV and JD**")
            st.write(", ".join(analysis["matched"][:160]) or "No overlap detected by this simple comparison.")
        with right:
            st.markdown("**JD terms not detected in CV**")
            st.write(", ".join(analysis["missing"][:160]) or "No missing terms detected by this simple comparison.")
        st.markdown("#### ATS-readiness checklist")
        checks = {
            "Has a professional summary/profile section": "summary" in analysis["sections"],
            "Has an experience section": "experience" in analysis["sections"],
            "Has an education section": "education" in analysis["sections"],
            "Has a skills section": "skills" in analysis["sections"],
            "Has a projects section (if relevant)": "projects" in analysis["sections"],
            "Includes measurable achievements where truthful": bool(re.search(r"\b\d+\s*(%|percent|users|systems|devices|alerts|years|months|hours|days)\b", analysis["resume"], re.I)),
            "Contains no tables/columns/icons that could confuse parsing": None,
            "Contact details and dates are consistent": None,
        }
        for label, result in checks.items():
            if result is True:
                st.success("✓ " + label)
            elif result is False:
                st.warning("Review: " + label)
            else:
                st.info("Manual check: " + label)
        st.markdown("#### Tailoring worksheet draft")
        st.write("This is a starting worksheet, not a fabricated final CV. It keeps your original CV text and provides an editable summary prompt plus keyword gaps; manually rewrite bullets using only true experience.")
        st.text_area("Editable draft", value=analysis["draft"], height=360, key="cv_draft_editor")
        st.download_button("Download tailoring worksheet (.txt)", data=st.session_state.get("cv_draft_editor", analysis["draft"]), file_name="careerpilot_cv_tailoring_worksheet.txt", mime="text/plain")
        if st.button("Save current CV to My Details", key="save_cv_from_optimizer"):
            current = get_profile()
            current["resume_text"] = analysis["resume"]
            save_profile(current)
            st.success("Base CV saved to your private cloud profile.")

with helper_tab:
    st.subheader("Prepare a stronger application")
    st.write("Create editable application materials and use the CareerPilot browser extension to autofill supported job-portal forms using your saved profile. CareerPilot never clicks Submit for you.")

    with st.expander("⚡ Set up browser autofill — one-time setup", expanded=True):
        st.markdown("""
        **What this does**

        CareerPilot's browser extension can fill supported, currently empty text fields and dropdowns on job application pages using the details saved under **My Details**. You must review every field and submit the application yourself.

        **Step 1 — Complete your CareerPilot profile**
        1. Open **My Details**.
        2. Enter your contact details, education, experience, skills and base CV.
        3. Click **Save details**.

        **Step 2 — Download the extension**
        Download the ZIP below and extract it to a folder on your computer. Keep the extracted folder somewhere you will not accidentally delete it.
        """)
        extension_path = APP_DIR / "CareerPilot_Browser_Autofill.zip"
        if extension_path.exists():
            st.download_button(
                "⬇️ Download CareerPilot Autofill Extension (.zip)",
                data=extension_path.read_bytes(),
                file_name="CareerPilot_Browser_Autofill.zip",
                mime="application/zip",
                key="download_careerpilot_extension",
                use_container_width=True,
            )
        else:
            st.warning("The extension ZIP is not present in the app repository yet. Add CareerPilot_Browser_Autofill.zip beside CareerPilot_Cloud.py in the GitHub repository, then redeploy.")

        st.markdown("""
        **Step 3 — Install it in Chrome or Edge**
        1. In Chrome, open `chrome://extensions`. In Microsoft Edge, open `edge://extensions`.
        2. Turn on **Developer mode**.
        3. Click **Load unpacked**.
        4. Select the extracted extension folder — the folder containing `manifest.json`.
        5. Pin CareerPilot Autofill to the browser toolbar if you want quick access.

        **Step 4 — Connect your account**
        1. Click the CareerPilot Autofill extension icon.
        2. Enter the Supabase project URL and the **public anon/publishable key** provided by the CareerPilot administrator, if these are not already filled in.
        3. Sign in using your own CareerPilot account credentials.
        4. Keep your CareerPilot profile up to date in **My Details**.

        **Step 5 — Autofill a job application**
        1. Sign in to the job portal normally and open the application form.
        2. Click the extension icon and choose **Autofill this page**.
        3. Check every filled field, correct anything that is wrong, and complete any unanswered questions.
        4. Upload your CV or other files manually if the portal requests them.
        5. Click the job portal's **Submit** button yourself.

        **Important limitations**
        - Each user installs and connects the extension on their own browser once.
        - Autofill supports common text fields and dropdowns; not every job portal or field will be recognised.
        - It does not submit applications, answer consent/demographic questions, bypass CAPTCHA or MFA, or upload files automatically.
        - Never enter a Supabase service-role/secret key in the extension. Use only the public anon/publishable key.
        - On a shared computer, sign out of the extension when finished.
        """)

    h1, h2 = st.columns(2)
    with h1:
        app_company = st.text_input("Company", key="helper_company")
        app_title = st.text_input("Job title", key="helper_title")
        app_url = st.text_input("Job listing URL", key="helper_url")
        recruiter_name = st.text_input("Recruiter / contact name (optional)", key="helper_recruiter")
    with h2:
        app_location = st.text_input("Job location / work mode", key="helper_location")
        app_type = st.selectbox("Material to generate", ["Cover letter", "Application email", "Recruiter LinkedIn message", "Follow-up email", "Interview preparation"], key="helper_type")
        applicant_name = st.text_input("Your name", value=profile.get("full_name", ""), key="helper_name")
        applicant_email = st.text_input("Your email", value=profile.get("email", ""), key="helper_email")
    helper_cv = st.text_area("Relevant CV text", value=profile.get("resume_text", ""), height=200, key="helper_cv")
    helper_jd = st.text_area("Job description / requirements", height=200, key="helper_jd")
    if st.button("Generate application draft", type="primary", key="generate_helper"):
        if not app_title.strip() or not helper_jd.strip():
            st.error("Enter the job title and job description so the draft can be relevant.")
        else:
            name = applicant_name.strip() or "[Your Name]"
            contact = applicant_email.strip() or "[Your Email]"
            company = app_company.strip() or "[Company]"
            role = app_title.strip()
            recruiter = recruiter_name.strip() or "Hiring Team"
            # Keep the generated copy grounded: no fabricated claims or assumed qualifications.
            relevant, _, _ = keyword_analysis(helper_cv, helper_jd)
            shared_terms = sorted((tokens(helper_cv) & tokens(helper_jd)) - STOPWORDS)[:8]
            evidence = ", ".join(shared_terms) if shared_terms else "[insert 2–3 relevant skills or projects you can substantiate]"
            if app_type == "Cover letter":
                content = f"Dear {recruiter},\n\nI am writing to apply for the {role} position at {company}. My background includes {evidence}. I am interested in this opportunity because it aligns with the areas described in the role requirements.\n\nIn my application, I would highlight the projects and experience most relevant to {role}, including specific examples and outcomes that I can verify. I would welcome the opportunity to discuss how my background matches your team's needs.\n\nThank you for your time and consideration.\n\nRegards,\n{name}\n{contact}"
            elif app_type == "Application email":
                content = f"Subject: Application for {role} — {name}\n\nDear {recruiter},\n\nPlease find my application for the {role} position at {company}. My relevant background includes {evidence}. I have attached my CV for your review and would appreciate the opportunity to discuss my suitability for the role.\n\nThank you for your consideration.\n\nRegards,\n{name}\n{contact}"
            elif app_type == "Recruiter LinkedIn message":
                content = f"Hello {recruiter}, I noticed the {role} opportunity at {company}. My background includes {evidence}, and I am interested in learning more about the role. Would you be open to sharing the application process or considering my profile? Thank you — {name}."
            elif app_type == "Follow-up email":
                content = f"Subject: Follow-up — {role} application\n\nDear {recruiter},\n\nI am following up on my application for the {role} position at {company}. I remain interested in the opportunity and would be grateful for any update you can share about the process.\n\nThank you for your time.\n\nRegards,\n{name}\n{contact}"
            else:
                score, matched, missing = keyword_analysis(helper_cv, helper_jd)
                content = f"INTERVIEW PREPARATION — {role} at {company}\n\n1. Prepare a 60-second introduction connected to this role.\n2. Prepare truthful STAR examples for teamwork, problem solving, ownership, and learning from mistakes.\n3. Review the following JD terms that also appear in your CV: {', '.join(matched[:25]) or '[identify relevant experience]'}.\n4. Review these JD terms not detected in your CV and prepare an honest response if asked: {', '.join(missing[:25]) or 'No gaps detected by basic keyword comparison'}.\n5. Prepare questions about the team, success measures, work mode, and first 90 days.\n6. Never claim tools, certifications, or experience you do not have.\n\nJOB LOCATION / MODE: {app_location or '[confirm with employer]'}\n\nJOB DESCRIPTION NOTES:\n{helper_jd[:5000]}"
            st.session_state["helper_draft"] = content
            st.session_state["helper_save_meta"] = (company, role, app_url.strip(), app_type)
    if st.session_state.get("helper_draft"):
        st.markdown("#### Generated draft — review before sending")
        st.text_area("Editable application material", value=st.session_state["helper_draft"], height=360, key="helper_draft_editor")
        st.download_button("Download draft (.txt)", data=st.session_state.get("helper_draft_editor", st.session_state["helper_draft"]), file_name="careerpilot_application_draft.txt", mime="text/plain")
        if st.button("Save this role to application tracker", key="helper_save_application"):
            company, title, url, material_type = st.session_state.get("helper_save_meta", ("", "", "", ""))
            if not company.strip() or not title.strip():
                st.warning("Enter the company and job title above, then generate the draft again.")
            else:
                add_application(company, title, url, "Interested", "", f"Created {material_type} draft on {date.today().isoformat()}")
                st.success("Role saved to tracker.")

with profile_tab:
    st.subheader("Your profile & base CV")
    st.caption("Profile and base CV are stored in your private Supabase cloud profile.")
    with st.form("profile_form"):
        p1, p2 = st.columns(2)
        with p1:
            full_name = st.text_input("Full name", value=profile.get("full_name", ""))
            email = st.text_input("Email", value=profile.get("email", ""))
            phone = st.text_input("Phone", value=profile.get("phone", ""))
        with p2:
            profile_city = st.text_input("Preferred location / city", value=profile.get("city", ""))
            linkedin = st.text_input("LinkedIn URL", value=profile.get("linkedin", ""))
            portfolio = st.text_input("Portfolio / GitHub URL", value=profile.get("portfolio", ""))
            country = st.text_input("Country of residence", value=profile.get("country", ""))
        st.markdown("#### Autofill profile fields")
        a1, a2 = st.columns(2)
        with a1:
            education = st.text_area("Education (degrees, institutions, dates)", value=profile.get("education", ""), height=100)
            experience = st.text_area("Work experience summary", value=profile.get("experience", ""), height=130)
            skills = st.text_area("Skills / technologies", value=profile.get("skills", ""), height=100)
        with a2:
            years_experience = st.text_input("Years of experience", value=profile.get("years_experience", ""))
            notice_period = st.text_input("Notice period / availability", value=profile.get("notice_period", ""))
            salary_expectation = st.text_input("Salary expectation (include currency)", value=profile.get("salary_expectation", ""))
            work_authorization = st.text_input("Work authorization / sponsorship answer (only if applicable)", value=profile.get("work_authorization", ""))
        saved_resume = st.text_area("Base CV text", value=profile.get("resume_text", ""), height=280)
        save_details = st.form_submit_button("Save details", type="primary")
        if save_details:
            save_profile({"full_name": full_name, "email": email, "phone": phone, "city": profile_city, "linkedin": linkedin, "portfolio": portfolio, "resume_text": saved_resume, "education": education, "experience": experience, "skills": skills, "country": country, "years_experience": years_experience, "notice_period": notice_period, "salary_expectation": salary_expectation, "work_authorization": work_authorization})
            st.success("Profile and base CV saved to your private cloud profile.")
            st.rerun()

with tracker_tab:
    st.subheader("Your application pipeline")
    try:
        rows = list_applications()
    except Exception as exc:
        st.error(f"Could not load your cloud application tracker: {exc}")
        rows = []
    if rows:
        st.caption(f"{len(rows)} tracked application(s)")
        for row in rows:
            with st.container(border=True):
                top1, top2 = st.columns([3, 1])
                with top1:
                    st.markdown(f"**{row['title'] or 'Untitled role'}** — {row['company'] or 'Company not specified'}")
                    if row["url"]:
                        st.markdown(f"[Open listing]({row['url']})")
                    st.caption(f"Created: {row['created_at'] or 'Unknown'} · Applied: {row['applied_on'] or 'Not recorded'}")
                    if row["notes"]:
                        st.write(row["notes"])
                with top2:
                    st.write(f"**{row['status'] or 'Interested'}**")
                with st.expander("Edit application"):
                    with st.form(f"edit_application_{row['id']}"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            edit_company = st.text_input("Company", value=row["company"] or "", key=f"ec_{row['id']}")
                            edit_title = st.text_input("Job title", value=row["title"] or "", key=f"et_{row['id']}")
                            edit_url = st.text_input("URL", value=row["url"] or "", key=f"eu_{row['id']}")
                        with ec2:
                            old_status = row["status"] if row["status"] in STATUSES else "Interested"
                            edit_status = st.selectbox("Status", STATUSES, index=STATUSES.index(old_status), key=f"es_{row['id']}")
                            try:
                                default_date = date.fromisoformat(row["applied_on"]) if row["applied_on"] else None
                            except ValueError:
                                default_date = None
                            edit_date = st.date_input("Applied on", value=default_date, key=f"ed_{row['id']}")
                        edit_notes = st.text_area("Notes", value=row["notes"] or "", key=f"en_{row['id']}")
                        save_edit = st.form_submit_button("Save changes")
                        if save_edit:
                            update_application(row["id"], {"company":edit_company.strip(),"title":edit_title.strip(),"url":edit_url.strip(),"status":edit_status,"applied_on":edit_date.isoformat() if edit_date else "","notes":edit_notes.strip()})
                            st.success("Application updated.")
                            st.rerun()
                confirm_key = f"confirm_delete_{row['id']}"
                if st.checkbox("Enable delete", key=confirm_key):
                    if st.button("Delete this application", key=f"delete_{row['id']}"):
                        delete_application(row["id"])
                        st.success("Application deleted.")
                        st.rerun()
    else:
        st.info("No applications tracked yet. Add one from Portal Search or the Application Helper.")
    st.divider()
    st.markdown("#### Add application manually")
    with st.form("manual_application"):
        mc1, mc2 = st.columns(2)
        with mc1:
            manual_company = st.text_input("Company", key="manual_company")
            manual_title = st.text_input("Job title", key="manual_title")
            manual_url = st.text_input("Job URL", key="manual_url")
        with mc2:
            manual_status = st.selectbox("Status", STATUSES, key="manual_status")
            manual_date = st.date_input("Application date", value=None, key="manual_date")
        manual_notes = st.text_area("Notes", key="manual_notes")
        if st.form_submit_button("Add application"):
            if not manual_company.strip() or not manual_title.strip():
                st.error("Company and job title are required.")
            else:
                add_application(manual_company, manual_title, manual_url, manual_status, manual_date.isoformat() if manual_date else "", manual_notes)
                st.success("Application added.")
                st.rerun()

st.divider()
st.markdown("<div class=\"cp-footer\">CareerPilot · Private cloud career workspace · Review every vacancy and all CV claims on the employer’s original site before applying.</div>", unsafe_allow_html=True)
