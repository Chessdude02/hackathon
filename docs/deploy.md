# Deploying the app (Streamlit Community Cloud)

Decision: D-28. Only the repo owner can do this, because Streamlit Cloud
deploys from a GitHub account that owns or administers the repo.

## Steps (about 10 minutes)

1. Go to https://share.streamlit.io and sign in with the GitHub account that
   owns `Chessdude02/hackathon`.
2. Click **Create app**, then **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `Chessdude02/hackathon`
   - Branch: `main`
   - Main file path: `app.py`
   - Python version (under Advanced settings): 3.11
4. Under **Advanced settings → Secrets**, paste one line (with the real key):
   ```
   FEATHERLESS_API_KEY = "paste-the-key-here"
   ```
   Never put the key in the repo.
5. Click **Deploy**. The first build installs `requirements.txt` and takes a
   few minutes.

## Check after the first deploy

- Choose **Use demo data**. The first time, a spinner shows for about 10
  seconds while the app builds the demo files. Then the mapping step appears.
- Click **Rank clients**. The ranked list should show 48 clients.
- Under **Scope-creep signals (beta)**, labels should load from the saved file
  at once (no "Label them now" button). If the button appears, the demo files
  do not match the saved labels: tell the team before clicking it, because it
  would spend LLM credits.
- Open a client in **5. Client detail**. The explanation should appear with no
  "standard wording" note. If every client shows the note, the key is not
  reaching the app (see below).

### If the key does not reach the app

Streamlit Cloud is expected to expose top-level secrets as environment
variables, which is what `llm.py` reads. We have not tested this yet. If
explanations always fall back to standard wording on the deployed app but work
locally, report it; the fix is a two-line change in `app.py` that copies
`st.secrets["FEATHERLESS_API_KEY"]` into the environment.

## Before judging and recording

- A free app sleeps after some days without visits. Open the link the day
  before judging and again on the morning of the deadline.
- Record the demo video from the deployed app, not a laptop, so the video
  matches what judges see.
- Check the Featherless balance on Friday. The demo itself spends nothing on
  saved labels and explanations; only new uploads or new clients cost credits.
