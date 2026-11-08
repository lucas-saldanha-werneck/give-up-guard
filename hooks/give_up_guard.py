#!/usr/bin/env python3
"""Stop hook: hold back, once, a final answer that gives up without really trying.

It blocks the stop (and sends Claude a short instruction) when the last answer:
  1. hands the task back to the user ("I can't do X", "you'll need to click...")
     without listing the routes it tried, and the step isn't human-only
     (captcha, 2FA, payment, biometrics, QR code);
  2. claims a tool, command or option "doesn't exist" without saying where it looked;
  3. asks the user for data (email, login, token...) without saying where it looked;
  4. lists something as "not checked" without saying why it can't be checked now.

Patterns live in patterns/*.json (one file per language) and in any extra folder
given by GIVE_UP_GUARD_PATTERNS or ~/.config/give-up-guard/patterns/. Text is
lowercased and accents are stripped before matching, so write patterns without accents.

Loop protection: never blocks when stop_hook_active is set (so at most once in a row).
Fails silently: an error here must never stop a session.
"""
import glob, json, os, re, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = ("give_up", "tried", "human_only", "not_exists", "searched", "asks_data", "not_checked", "why_not")

REASON_GIVE_UP = (
    "Before handing this task back to the user: did you try at least two different routes and look for "
    "a tool that could do it (CLI, API, installed skills or MCP servers, docs, issue trackers, project notes)? "
    "If you did, rewrite the answer with a line 'Routes tried:' listing each route and the real error. "
    "If you didn't, try now. Hand back only steps that truly need a human (captcha, 2FA, payment) and say why. "
    "(give-up-guard: verify before you claim)")
REASON_NOT_EXISTS = (
    "You said something doesn't exist. Look now (official docs, `--help`, command lists, config files, "
    "project notes). Then write 'Searched in: ...', or change the claim to "
    "'I didn't find it in X; I didn't look in Y'. (give-up-guard: verify before you claim)")
REASON_ASKS = (
    "Before asking the user for this data: look for it yourself (project files, notes and memory, config, "
    "environment, the password manager or tools you have access to). If you looked, write "
    "'Searched in: ...' and then ask. (give-up-guard: verify before you claim)")
REASON_NOT_CHECKED = (
    "You listed something as not checked. Check now whatever you can with the tools you have (open the "
    "file, run the command, read the real state). Keep on the list only what is impossible to check right "
    "now, and say why for each item. (give-up-guard: verify before you claim)")


def pattern_dirs():
    dirs = [os.path.join(os.path.dirname(HERE), "patterns")]
    extra = os.environ.get("GIVE_UP_GUARD_PATTERNS")
    if extra:
        dirs += extra.split(os.pathsep)
    dirs.append(os.path.join(os.path.expanduser("~"), ".config", "give-up-guard", "patterns"))
    return dirs


def load_patterns():
    lists = {k: [] for k in KEYS}
    for d in pattern_dirs():
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            for k in KEYS:
                for p in data.get(k, []) or []:
                    try:
                        re.compile(p)
                        lists[k].append(p)
                    except re.error:
                        continue
    return {k: (re.compile("|".join("(?:%s)" % p for p in v)) if v else None) for k, v in lists.items()}


def hit(rx, t):
    return bool(rx and rx.search(t))


def pick_reason(t, P):
    tried = hit(P["tried"], t)
    if hit(P["give_up"], t) and not tried and not hit(P["human_only"], t):
        return REASON_GIVE_UP
    if hit(P["not_exists"], t) and not tried and not hit(P["searched"], t):
        return REASON_NOT_EXISTS
    if hit(P["asks_data"], t) and not tried:
        return REASON_ASKS
    if hit(P["not_checked"], t) and not hit(P["why_not"], t):
        return REASON_NOT_CHECKED
    return None


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def last_text(d):
    if isinstance(d.get("last_assistant_message"), str):
        return d["last_assistant_message"]
    path = d.get("transcript_path")
    if not path:
        return ""
    last = ""
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("type") != "assistant" or e.get("isSidechain"):
                continue
            texts = [b.get("text", "") for b in e.get("message", {}).get("content", []) or []
                     if isinstance(b, dict) and b.get("type") == "text"]
            if any(t.strip() for t in texts):
                last = "\n".join(texts)
    return last


def main():
    try:
        d = json.load(sys.stdin)
        if d.get("stop_hook_active"):
            return
        # Headless runs (`claude -p`) have no user to talk to; an extra turn would only
        # spoil the output a script reads. Set GIVE_UP_GUARD_HEADLESS=1 to check them too.
        if os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "sdk-cli" and os.environ.get("GIVE_UP_GUARD_HEADLESS") != "1":
            return
        # A quote is not a give-up: drop "...", “...” and `...` before matching.
        t = re.sub(r'"[^"\n]*"|“[^”\n]*”|`[^`\n]*`', " ", norm(last_text(d)))
        reason = pick_reason(t, load_patterns())
        if reason:
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    except Exception:
        return


if __name__ == "__main__":
    main()
