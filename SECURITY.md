# Security Policy

This repository is a security-hardened fork of
[sergebulaev/x-skills](https://github.com/sergebulaev/x-skills), maintained at
[leopiney/x-skills](https://github.com/leopiney/x-skills). Only the latest tag
of this fork is supported. Report issues privately via
[GitHub Security Advisories](https://github.com/leopiney/x-skills/security/advisories/new).

## Audit findings addressed (v1.0.39)

The upstream bundle (commit `28854d5`) was flagged on skills.sh by Gen Agent
Trust Hub (Fail, CRITICAL), Socket (Warn) and Snyk (Warn, MEDIUM).

| Finding | Source | What changed |
|---|---|---|
| COMMAND_EXECUTION: custom publishing script run via `subprocess.run` | Trust Hub | The "Tier 2 / DIY" backend and `X_SKILLS_CUSTOM_POSTER` were removed. No module in `lib/` imports `subprocess`/`shlex` or calls `os.system`, `exec` or `eval`. `scripts/check_security_boundaries.py` fails the build if any of that comes back. |
| INDIRECT_PROMPT_INJECTION / W011 third-party content exposure | Trust Hub, Snyk | The `## Untrusted content` rule now sits at the **top** of each reading skill, before any workflow step (it used to be at the bottom). `check_untrusted_rule.py` enforces the placement. In code, every fetched record is tagged `"untrusted": true`, and free-text fields are NFKC-normalized, stripped of zero-width/bidi/control characters and length-capped. Handles and ids are validated, fetches are capped at 100 items, and `fetch_tweet_replies` only accepts genuine X tweet URLs. `lib.publish()` now fails closed unless called with `approved=True`. |
| EXTERNAL_DOWNLOADS: Apify / Pixfaro calls with user credentials | Trust Hub | The Apify token moved from the URL query string (`?token=`) to an `Authorization: Bearer` header, so it cannot leak into logs or error messages. All authenticated requests keep `allow_redirects=False`. |
| Credential source confusion (supports the above) | Review | `.env` used to be found by searching **upward from the working directory**, so any cloned repo could swap in someone else's Publora/Pixfaro/Apify keys and receive your approved drafts. Credentials now load only from `~/.config/x-skills/.env` (or `$XDG_CONFIG_HOME`) and the installed skill folder, and only allowlisted names are loaded. |
| FileRep "1 file identified as malware" (file not named) | Trust Hub | The report does not name the file, and its own notes call the `url_parser.py` detection a false positive. To shrink the opaque surface anyway, this fork removes the generated `.codex-marketplace/` tree, which was a second, unhardened copy of `lib/` and every skill that shipped into installs. It also removes the binary marketing images (`hero.png`, `social-preview.jpg`), which cannot be reviewed as text. |
| Anomaly: personal repo distributing a skill that handles SaaS publishing credentials | Socket (`x-post-writer/SKILL.md`) | Provenance is now this fork, which you control. The README installs from a pinned release tag instead of a moving branch. The upstream "star the repo" instruction to the agent was removed from `SKILL.md`. The flagged file lived in the removed `.codex-marketplace/` tree. |
| W012 unverifiable external dependency (install from an individual's repo) | Snyk | Install from this fork at a reviewed tag. Python dependencies are exact-pinned, and `requirements-lock.txt` carries sha256 hashes (`pip install --require-hashes -r requirements-lock.txt`). |

## Data flow

- **Apify** (`api.apify.com`): receives the handle, search query or tweet id
  you ask about. Runs only when `APIFY_TOKEN` is set.
- **Publora** (`api.publora.com`): receives the approved draft text and your
  platform id. Runs only when `PUBLORA_API_KEY` and `X_PLATFORM_ID` are set,
  and only through `publish(..., approved=True)`. Replies and quotes are never
  auto-posted.
- **Pixfaro** (`api.pixfaro.com`): receives image prompts and overlay text.
  Runs only when `PIXFARO_TOKEN` is set.
- Nothing else is contacted, and nothing is executed locally.

## Residual risk

The prompt-injection controls reduce risk but cannot remove it. A language
model reading text written by strangers can still be steered. Keep the human
approval step, and read every draft before you approve it, especially drafts
built from fetched replies.
