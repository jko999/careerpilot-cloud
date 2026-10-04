# CareerPilot Browser Autofill (Chrome / Edge)

This is a separate Manifest V3 browser extension. It does not modify the existing Streamlit app or Supabase schema.

## Important connection detail
The hosted Streamlit app's signed-in session is server-side and is not automatically shared with browser extensions. Therefore, sign in here separately with the same CareerPilot account. The extension uses Supabase Auth and the existing user's row-level security to fetch only that account's `careerpilot_profiles` row.

## Install
1. Extract `CareerPilot_Browser_Autofill.zip` to a folder on your computer.
2. Open `chrome://extensions` in Chrome or `edge://extensions` in Edge.
3. Turn on **Developer mode**.
4. Select **Load unpacked** and choose the extracted `CareerPilot_Browser_Autofill` folder (the folder containing `manifest.json`).
5. Click the extension icon and pin CareerPilot if you want quick access.

## Connect
1. In the extension popup, enter your Supabase project URL: `https://nnzqksuacyiyrmxfiuoh.supabase.co`.
2. Enter the project's **public publishable key** (or legacy public anon key) from Supabase project API settings. Never paste a `service_role` or secret key.
3. Sign in using the same email/password you use for CareerPilot.
4. Ensure your My Details profile is saved in CareerPilot before autofilling.

## Use
1. Open a job application page in your normal signed-in Chrome/Edge session.
2. Click CareerPilot Autofill → **Autofill this page**.
3. Review every populated field and correct anything that is wrong. Submit the application yourself.

## Scope and safety
- Fills only empty, supported text inputs, textareas, and some selects when labels look like a clear match.
- Does not submit forms, click buttons, select consent/demographic/eligibility answers, upload files, solve CAPTCHAs, or bypass MFA.
- The resume text is not automatically pasted into every “resume” or long-answer field; those fields need manual review.
- Some portals use custom controls, shadow DOM, or multi-step forms that may not be supported.
- The extension stores the Supabase session token, project URL, public key, and profile locally in Chrome/Edge extension storage. Sign out when using a shared computer. Do not install on a device you do not trust.
- The extension has not been tested against your specific employer portals yet. Validate on a non-submitted test form first.

## Troubleshooting
- If profile fetch fails, check the Supabase URL/key, confirm that the signed-in account can log into CareerPilot, and confirm the `careerpilot_profiles` table has a `user_id` column with owner-only SELECT RLS policy.
- If the app's profile table uses a different column name or RLS policy, the extension will show an error rather than bypassing security.
