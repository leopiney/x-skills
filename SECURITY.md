# Security Policy

This repository is a security-hardened fork of
[sergebulaev/x-skills](https://github.com/sergebulaev/x-skills), maintained at
[leopiney/x-skills](https://github.com/leopiney/x-skills). Only the latest tag
of this fork is supported. Report issues privately via
[GitHub Security Advisories](https://github.com/leopiney/x-skills/security/advisories/new).

## Round 1 (v1.0.39): audit findings addressed

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

## Round 2 (v1.0.40): after the v1.0.39 re-scan

skills.sh re-scanned v1.0.39 (commit `00393bb`): Socket **Pass**, Snyk Warn
(W011, W012, W013), Trust Hub still Fail. Fixes:

| Finding | Source | What changed |
|---|---|---|
| FileRep "1 file identified as malware" (still CRITICAL) | Trust Hub | FileRep judges a file by its hash. `lib/url_parser.py` was byte-identical to upstream, and upstream's audit named it as the automated malware hit (a false positive: plain URL regexes plus a self-test full of fake attacker URLs). The self-test moved to `tests/test_url_parser.py`, outside the installed skill, so the shipped file has a new hash. |
| DYNAMIC_EXECUTION: `importlib` in `scripts/check_mcp_mapping.py` | Trust Hub | The skill now lives in `x-marketing-secure/`, and only that folder is installed. CI scripts, tests, `.github/` and maintainer docs stay in the repo and never reach `~/.agents/skills`. |
| W013: instructions to push tags and create releases | Snyk | Same: `AGENTS.md`/`CLAUDE.md` are no longer installed, and they now say agents tag or release only when asked. `check_security_boundaries.py` fails if the bundle ever carries such instructions, dev tooling, binaries, dynamic imports or raw network helpers. |
| W012: tag not cryptographically verified | Snyk | Release tags are SSH-signed. Verify with `git -c gpg.ssh.allowedSignersFile=allowed_signers verify-tag v1.0.40`. The "individually owned repo" part is inherent to a fork. |
| CREDENTIALS_UNSAFE | Trust Hub | On POSIX, a `.env` is ignored (with a warning) unless it is owned by you and `chmod 600`. Publora `media_urls` must be plain `https://` URLs. |

Expected to remain because they describe what the skill does:
DATA_EXFILTRATION (drafts go to Publora, prompts to Pixfaro, queries to Apify),
EXTERNAL_DOWNLOADS (hash-pinned `pip install`), and INDIRECT_PROMPT_INJECTION /
W011 (it reads tweets written by strangers).

## Round 3 (v1.0.41): renamed to `x-marketing-secure`

skills.sh audits a skill automatically only on its first install, and it
documents no way to request a re-scan. So v1.0.40 kept showing the v1.0.39
results. The skill and its folder are renamed `x-marketing-secure`, which gives
it a fresh skills.sh identity that gets audited against the current code. No
code changed from v1.0.40.

## Round 4 (v1.0.42): reading replies is opt-in

Snyk's remaining W011 (MEDIUM, 0.30) singled out `fetch_tweet_replies`:
anyone on X can reply to the user's tweet, and the audience-insights workflow
read replies by default.

- `fetch_tweet_replies` now raises `RepliesNotRequested` unless called with
  `user_requested=True`, before any request is sent. Replies are capped at 30.
- `x-audience-insights` no longer reads replies in its workflow. A separate
  "Reading replies (opt-in only)" section allows it only when the user
  explicitly asks to read the replies on a specific tweet. The MCP connector
  path documents the same condition.
- `check_security_boundaries.py` fails if the opt-in default changes or a
  documented call omits `user_requested=True`. It now also rejects raw
  invisible/bidi characters anywhere in the repo.
- The behavior tests moved into the repo (`tests/test_security_behavior.py`)
  and run in CI.

W011 is expected to remain at some level, because the skill still reads tweets
written by strangers when asked.

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
