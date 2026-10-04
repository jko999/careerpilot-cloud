const $ = id => document.getElementById(id);
const PROFILE_COLUMNS = [
  "full_name","email","phone","city","linkedin","portfolio","resume_text",
  "education","experience","skills","country","years_experience",
  "notice_period","salary_expectation","work_authorization"
];
let session = null;
let profile = null;

function status(message, error=false) {
  $("status").textContent = message;
  $("status").style.color = error ? "#ffb4a9" : "#c7f36b";
}
function cleanUrl(v) { return (v || "").trim().replace(/\/+$/, ""); }
async function loadSaved() {
  const data = await chrome.storage.local.get(["projectUrl","anonKey","session","profile"]);
  $("projectUrl").value = data.projectUrl || "https://nnzqksuacyiyrmxfiuoh.supabase.co";
  $("anonKey").value = data.anonKey || "";
  session = data.session || null;
  profile = data.profile || null;
  if (session && profile) showConnected();
}
function showConnected() {
  $("config").hidden = true;
  $("connected").hidden = false;
  $("account").textContent = `Signed in as ${session?.user?.email || "CareerPilot user"}`;
}
function showLogin() {
  $("config").hidden = false;
  $("connected").hidden = true;
}
function apiHeaders(token) {
  return {"apikey": $("anonKey").value.trim(), "Authorization": `Bearer ${token}`, "Content-Type":"application/json"};
}
async function requestProfile() {
  const project = cleanUrl($("projectUrl").value);
  const key = $("anonKey").value.trim();
  if (!project.startsWith("https://") || !key) throw new Error("Enter the Supabase project URL and public publishable/anon key.");
  let token = session?.access_token;
  if (session?.expires_at && Date.now() > session.expires_at - 60000 && session.refresh_token) {
    const rr = await fetch(`${project}/auth/v1/token?grant_type=refresh_token`, {
      method:"POST", headers:{"apikey":key,"Content-Type":"application/json"},
      body:JSON.stringify({refresh_token:session.refresh_token})
    });
    const rd = await rr.json();
    if (!rr.ok) throw new Error(rd.msg || rd.message || "Session expired. Please sign in again.");
    session = {...rd, expires_at:Date.now() + (rd.expires_in || 3600)*1000};
    token = session.access_token;
  }
  if (!token) throw new Error("Please sign in first.");
  const uid = session.user?.id;
  if (!uid) throw new Error("Could not identify the signed-in user. Please sign in again.");
  const url = `${project}/rest/v1/careerpilot_profiles?user_id=eq.${encodeURIComponent(uid)}&select=${PROFILE_COLUMNS.join(",")}&limit=1`;
  const response = await fetch(url, {headers:apiHeaders(token)});
  const rows = await response.json();
  if (!response.ok) throw new Error(rows.message || rows.details || "Could not load your profile. Check table permissions and RLS.");
  if (!Array.isArray(rows) || !rows.length) throw new Error("No CareerPilot profile row was returned for this account. Open CareerPilot and save My Details first.");
  profile = rows[0];
  await chrome.storage.local.set({projectUrl:cleanUrl(project),anonKey:key,session,profile});
  return profile;
}
$("login").addEventListener("click", async () => {
  try {
    $("login").disabled = true; status("Signing in…");
    const project = cleanUrl($("projectUrl").value), key = $("anonKey").value.trim();
    const email = $("email").value.trim(), password = $("password").value;
    if (!project.startsWith("https://") || !key || !email || !password) throw new Error("Enter the project URL, public key, email, and password.");
    const response = await fetch(`${project}/auth/v1/token?grant_type=password`, {
      method:"POST",headers:{"apikey":key,"Content-Type":"application/json"},
      body:JSON.stringify({email,password})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.msg || data.message || data.error_description || "Sign-in failed.");
    session = {...data,expires_at:Date.now()+(data.expires_in || 3600)*1000};
    await chrome.storage.local.set({projectUrl:project,anonKey:key,session});
    await requestProfile();
    showConnected(); status("Connected. Your profile is loaded.");
  } catch (e) { status(e.message || "Sign-in failed.", true); }
  finally { $("login").disabled = false; $("password").value = ""; }
});
$("refresh").addEventListener("click", async () => {
  try { status("Refreshing profile…"); await requestProfile(); status("Profile refreshed."); }
  catch(e) { status(e.message || "Could not refresh profile.", true); }
});
$("logout").addEventListener("click", async () => {
  session = null; profile = null;
  await chrome.storage.local.remove(["session","profile"]);
  showLogin(); status("Signed out. Saved project URL/key remain on this browser.");
});
$("fill").addEventListener("click", async () => {
  try {
    status("Loading latest profile…");
    const p = await requestProfile();
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab?.id || !/^https?:/.test(tab.url || "")) throw new Error("Open a job application page in a normal browser tab first.");
    const result = await chrome.scripting.executeScript({target:{tabId:tab.id},func:autofillSupportedFields,args:[p]});
    const r = result?.[0]?.result || {filled:0,review:0};
    status(`Filled ${r.filled} field(s). ${r.review} field(s) need manual review. Please verify before continuing.`);
  } catch(e) { status(e.message || "Autofill failed.", true); }
});
function autofillSupportedFields(p) {
  const norm = s => (s || "").toLowerCase().replace(/[_-]+/g," ").replace(/[^a-z0-9+#. ]/g," ").replace(/\s+/g," ").trim();
  const safeMap = [
    {key:"full_name", patterns:[/\b(full name|your name|candidate name|first and last name|name)\b/], exclude:/company|recruiter|reference|emergency|manager|middle name/},
    {key:"email", patterns:[/\b(email|e mail|email address)\b/], exclude:/recruiter|manager|reference/},
    {key:"phone", patterns:[/\b(phone|mobile|telephone|contact number)\b/], exclude:/emergency|reference|recruiter/},
    {key:"city", patterns:[/\b(city|current location|city of residence|town)\b/], exclude:/preferred|relocat|job location|office location/},
    {key:"linkedin", patterns:[/\blinkedin(profile| url| link)?\b/]},
    {key:"portfolio", patterns:[/\b(portfolio|personal website|website url|github profile|personal url)\b/]},
    {key:"education", patterns:[/\b(education|degree|university|college|qualification)\b/], exclude:/highest level.*completed/},
    {key:"experience", patterns:[/\b(work experience|professional experience|employment history|experience summary)\b/]},
    {key:"skills", patterns:[/\b(skills|technical skills|key competencies)\b/]},
    {key:"country", patterns:[/\b(country of residence|current country|country)\b/], exclude:/citizenship|nationality|work authorization|visa/},
    {key:"years_experience", patterns:[/\b(years of experience|total experience|professional experience in years)\b/], exclude:/specific technology|management/},
    {key:"notice_period", patterns:[/\b(notice period|availability to join|joining time)\b/]},
    {key:"salary_expectation", patterns:[/\b(expected salary|salary expectation|desired salary|salary requirement|compensation expectation)\b/]}
  ];
  const fields = [...document.querySelectorAll("input:not([type]),input[type='text'],input[type='email'],input[type='tel'],input[type='url'],input[type='number'],textarea,select")];
  let filled=0, review=0;
  const labelText = el => {
    const parts = [];
    if (el.labels) for (const l of el.labels) parts.push(l.innerText || l.textContent || "");
    const parent = el.closest("label"); if (parent) parts.push(parent.innerText || parent.textContent || "");
    const group = el.closest("fieldset"); if (group) { const legend=group.querySelector("legend"); if (legend) parts.push(legend.innerText || legend.textContent || ""); }
    parts.push(el.getAttribute("aria-label") || "", el.getAttribute("placeholder") || "", el.getAttribute("name") || "", el.id || "", el.getAttribute("autocomplete") || "");
    return norm(parts.join(" "));
  };
  const nativeSet = (el, value) => {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype :
      el instanceof HTMLSelectElement ? HTMLSelectElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto,"value")?.set;
    if (setter) setter.call(el,value); else el.value=value;
    el.dispatchEvent(new Event("input",{bubbles:true}));
    el.dispatchEvent(new Event("change",{bubbles:true}));
  };
  for (const el of fields) {
    if (el.disabled || el.readOnly || el.type==="hidden" || el.getAttribute("aria-hidden")==="true") continue;
    if (el.value && String(el.value).trim()) continue;
    const text = labelText(el);
    if (/\b(password|captcha|verification|otp|one time code|ssn|social security|national id|passport|visa status|sponsorship|work authorization|authorized to work|legally entitled|citizenship|gender|race|ethnicity|disability|veteran|criminal|consent|agree|salary currency|cover letter file|resume file|upload)\b/.test(text)) { review++; continue; }
    let chosen=null;
    for (const rule of safeMap) {
      if (!rule.patterns.some(re=>re.test(text))) continue;
      if (rule.exclude && rule.exclude.test(text)) continue;
      const value = String(p[rule.key] || "").trim();
      if (!value) continue;
      if (rule.key==="full_name" && /\b(first name|given name|last name|surname|family name)\b/.test(text)) continue;
      if (rule.key==="education" && el.tagName==="SELECT") continue;
      if (rule.key==="country" && el.tagName==="SELECT") continue;
      if (rule.key==="salary_expectation" && el.type==="number" && !/^\s*\d+(?:\.\d+)?\s*$/.test(value)) continue;
      chosen={key:rule.key,value}; break;
    }
    if (!chosen) {
      if (/\b(resume|cv|cover letter|motivation|bio|summary|about you|describe your|why do you|eligibility|authorization|sponsorship|visa|demographic|gender|disability)\b/.test(text)) review++;
      continue;
    }
    if (el.tagName==="SELECT") {
      const wanted=norm(chosen.value);
      const option=[...el.options].find(o=>norm(o.label||o.textContent)===wanted || norm(o.value)===wanted);
      if (!option) { review++; continue; }
      el.value=option.value; el.dispatchEvent(new Event("change",{bubbles:true})); filled++;
    } else {
      nativeSet(el,chosen.value); filled++;
    }
  }
  return {filled,review};
}
loadSaved().catch(e=>status(e.message || "Could not initialize extension.",true));
