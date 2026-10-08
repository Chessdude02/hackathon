# Security

The app is public (https://hackathon-qiv6graw7ewfv6lqndywtd.streamlit.app/) and the
repository is public. It is a hackathon demo, not a service for confidential data;
the screen says so. This file lists what is protected, how, and what is not.
Decision: D-35.

## Reporting a problem

Open a GitHub issue without the sensitive detail and ask for a private contact,
or contact the repository owner directly. Never post a key in an issue.

## What is protected, and how

| Risk | Protection | Where |
|---|---|---|
| The AI key leaks | Read only from the `FEATHERLESS_API_KEY` environment variable (Streamlit secrets when deployed). `.env` files are ignored by git. Checked on 2026-10-08: no key in any commit. | `src/clientprofit/llm.py`, `.gitignore` |
| A visitor spends the team's AI credits | Per browser session: at most 500 new request messages labelled by AI (more than that: keyword rule only) and at most 25 new AI explanations (then fixed wording). Above 200 new messages the screen asks first. After 5 failed calls in a row the app stops calling the provider. | `app.py` (`MAX_LIVE_LABELS`, `MAX_LIVE_EXPLANATIONS`, `ASK_BEFORE_LABELLING`), `scope/llm_detector.py` |
| A visitor's data is kept on the server | AI labels and explanations for uploaded files are kept in that browser session's memory only and are never written to disk. Only the demo data uses the saved files shipped with the repo. Uploaded files are not stored. | `app.py` (`session_store`), `scope/store.py` (`LabelStore(None)`) |
| Very large uploads slow or crash the server | Uploads are limited to 20 MB per file. | `.streamlit/config.toml` |
| Error messages show uploaded data | The browser shows where an error happened, not its message. | `.streamlit/config.toml` (`showErrorDetails`) |
| Uploaded text or AI text turns into links, images or HTML on the screen | Text from uploads and from the AI is escaped before it is shown; raw HTML is never enabled. | `explain.escape_markdown` |
| The AI invents numbers | Every number in an AI explanation must exist in the computed figures, or fixed wording is shown. The AI never does arithmetic. | `explain.check_numbers` (D-26) |
| Prompt injection in uploaded messages | A request label is accepted only if the reply is one of three fixed labels; anything else falls back to the keyword rule. Explanations pass the number check above. | `scope/llm_detector.parse_label` |
| A new package release changes the live app | Every package is pinned to the version the tests pass with. | `requirements.txt` |
| Unsafe code paths | No `eval`, `exec`, `pickle`, shell calls or raw HTML in the app; YAML is read with `safe_load`. | whole repo |

## What is NOT protected

- **No login.** Anyone with the link can use the app. Do not upload real client data.
- **Message text goes to an outside AI provider** (Featherless) when requests are uploaded and labelled. A real deployment needs a data agreement or a locally run model.
- **Limits are per browser session.** Someone opening many sessions can still spend credits; the provider account has a fixed prepaid balance, which caps the total loss.
- **Prompt injection can still change the wording** of an explanation on the uploader's own screen (not its numbers). It cannot reach other visitors.
- **No virus scanning** of uploads. Files are read as CSV text only, never run or opened by another program.
- **The demo data's saved labels and explanations are public** in this repository, by design.
