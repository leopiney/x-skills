#!/usr/bin/env python3
"""Trust boundaries this bundle is not allowed to reopen.

1. **Nothing in lib/ executes a process.** The upstream "DIY" tier ran a
   command named by X_SKILLS_CUSTOM_POSTER through subprocess. It was removed;
   no module in lib/ may import subprocess, call os.system/os.popen/os.exec*,
   eval/exec, or reference that variable again.
2. **.env is read only from fixed, user-owned locations, credentials only.**
   lib/_env.py keeps an allowlist (_DOTENV_VARIABLES) and must not search
   upward from the working directory (find_dotenv / usecwd / Path.cwd), which
   would let any cloned repo swap in someone else's API keys.
3. **No module may load a .env behind load_env's back.** A direct
   load_dotenv() call reopens boundary 2 for whatever imports it.
4. **Authenticated requests may not follow redirects**, and credentials ride
   headers, never the URL query string (no `params={"token": ...}`).

Run from the repo root:

    python3 scripts/check_security_boundaries.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
ENV = LIB / "_env.py"
POSTER = "X_SKILLS_CUSTOM_POSTER"
CLIENTS = ("publora_client.py", "apify_client.py", "youtube_client.py", "pixfaro_client.py")
DOTENV_CALL = re.compile(r"load_dotenv\s*\(")
CALL = re.compile(r"((?:self\._session|requests)\.(?:get|post|put|delete)\()")
EXEC = re.compile(
    r"\bimport\s+subprocess\b|\bfrom\s+subprocess\b|\bos\.(?:system|popen|exec\w*|spawn\w*)\s*\("
    r"|(?<![\w.])(?:eval|exec)\s*\(|\bimport\s+shlex\b|\bpty\.spawn\b"
)
CWD_SEARCH = re.compile(r"find_dotenv|usecwd|Path\.cwd\(|os\.getcwd\(")
TOKEN_IN_QUERY = re.compile(r"params\s*=\s*\{[^}]*(?:token|key|secret)", re.I)


def call_bodies(source: str):
    """(offset, body) for every HTTP call, parens matched so multi-line is fine."""
    for match in CALL.finditer(source):
        depth, i = 1, match.end()
        while depth and i < len(source):
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
            i += 1
        yield match.start(), source[match.end():i - 1]


def code_only(source: str) -> str:
    """Drop comments and docstrings so prose about removed features is allowed."""
    source = re.sub(r'"""(?:.|\n)*?"""', '""', source)
    source = re.sub(r"'''(?:.|\n)*?'''", "''", source)
    return re.sub(r"#[^\n]*", "", source)


def main() -> int:
    problems = []

    for path in sorted(LIB.glob("*.py")):
        code = code_only(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT)
        if EXEC.search(code):
            problems.append(f"{rel} executes or prepares a process/eval. lib/ must not run commands.")
        if POSTER in code:
            problems.append(f"{rel} references {POSTER}; the command-executing tier was removed.")

    env = code_only(ENV.read_text(encoding="utf-8"))
    if "_DOTENV_VARIABLES" not in env:
        problems.append("lib/_env.py has no _DOTENV_VARIABLES allowlist.")
    if DOTENV_CALL.search(env):
        problems.append("lib/_env.py calls load_dotenv(); use dotenv_values() on the allowlist.")
    if CWD_SEARCH.search(env):
        problems.append(
            "lib/_env.py searches for .env relative to the working directory. Only the "
            "fixed user config dir and the skill dir are allowed.")

    for path in sorted((ROOT / "scripts").glob("*.py")) + sorted(LIB.glob("*.py")):
        if path.name in ("_env.py", pathlib.Path(__file__).name):
            continue
        if DOTENV_CALL.search(code_only(path.read_text(encoding="utf-8"))):
            problems.append(
                f"{path.relative_to(ROOT)} calls load_dotenv() directly, bypassing lib/_env.py.")

    for name in CLIENTS:
        path = LIB / name
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        for offset, body in call_bodies(source):
            line = source[:offset].count("\n") + 1
            if "allow_redirects" not in body:
                problems.append(
                    f"lib/{name}:{line}: authenticated request without allow_redirects=False.")
            if TOKEN_IN_QUERY.search(body):
                problems.append(
                    f"lib/{name}:{line}: credential in the URL query string; use a header.")

    if problems:
        print("Security boundaries:\n" + "\n".join("  " + p for p in problems))
        return 1

    print("OK: lib/ runs no processes, .env loads credentials only from fixed paths, "
          "nothing loads it behind load_env, and credentials ride headers without redirects.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
