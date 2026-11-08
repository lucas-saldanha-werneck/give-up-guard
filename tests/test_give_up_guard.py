#!/usr/bin/env python3
"""Feeds sample Stop-hook JSON to the hook and checks whether it blocks."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "give_up_guard.py")


def run(payload, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_ENTRYPOINT", "GIVE_UP_GUARD_PATTERNS")}
    env["HOME"] = tempfile.mkdtemp()  # no user patterns
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
    out = p.stdout.strip()
    return p.returncode, (json.loads(out) if out else None)


def msg(text, **kw):
    return dict({"hook_event_name": "Stop", "last_assistant_message": text}, **kw)


CASES = [
    # (name, payload, env, expected reason prefix or None)
    ("en not checked", msg("Done.\n\nNot checked: the deploy log."), None, "You listed something as not checked"),
    ("en didn't test", msg("Fixed it. I didn't test the Windows path."), None, "You listed something as not checked"),
    ("en not checked + why", msg("Not verified: the email arrived, it requires 2FA on your phone."), None, None),
    ("pt nao conferi", msg("Pronto. Não conferi o arquivo final."), None, "You listed something as not checked"),
    ("pt nao conferi + why", msg("Não conferi o login: é impossível sem o código 2FA."), None, None),
    ("en give up", msg("I can't upload the file. You'll need to open the site and upload it."), None, "Before handing this task back"),
    ("en give up + tried", msg("I can't upload the file.\nRoutes tried: API (403), CLI (missing)."), None, None),
    ("en give up human only", msg("You'll need to solve the captcha on the page."), None, None),
    ("pt give up", msg("Não consigo enviar. Você precisa abrir o site."), None, "Before handing this task back"),
    ("en not exists", msg("There is no option for that in the CLI."), None, "You said something doesn't exist"),
    ("pt not exists", msg("Esse comando não existe nesta versão."), None, "You said something doesn't exist"),
    ("en not exists + searched", msg("There is no option for that. I didn't find it in --help."), None, None),
    ("en asks data", msg("What is your email for the account?"), None, "Before asking the user for this data"),
    ("quoted text is ignored", msg('The doc literally says "not checked" in the header.'), None, None),
    ("clean answer", msg("Done. Ran the tests: 12 passed."), None, None),
    ("loop protection", msg("Not checked: anything.", stop_hook_active=True), None, None),
    ("headless skipped", msg("Not checked: anything."), {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}, None),
    ("headless opt-in", msg("Not checked: anything."), {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli", "GIVE_UP_GUARD_HEADLESS": "1"}, "You listed"),
    ("bad stdin", "not json", None, None),
]


def main():
    fails = 0
    # transcript fallback
    tdir = tempfile.mkdtemp()
    tpath = os.path.join(tdir, "t.jsonl")
    with open(tpath, "w") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Not tested yet."}]}}) + "\n")
    CASES.append(("transcript fallback", {"transcript_path": tpath}, None, "You listed"))
    # extra pattern folder (another language)
    pdir = tempfile.mkdtemp()
    with open(os.path.join(pdir, "es.json"), "w") as f:
        json.dump({"not_checked": ["no (verifique|comprobe)"]}, f)
    CASES.append(("extra language folder", msg("Listo. No verifiqué el log."), {"GIVE_UP_GUARD_PATTERNS": pdir}, "You listed"))

    for name, payload, env, want in CASES:
        if isinstance(payload, str):
            env2 = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_ENTRYPOINT"}
            p = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True, env=env2)
            code, out = p.returncode, (p.stdout.strip() or None)
        else:
            code, out = run(payload, env)
        got = out.get("reason") if isinstance(out, dict) else out
        ok = code == 0 and ((want is None and got is None) or (want and got and got.startswith(want)
                                                               and out.get("decision") == "block"))
        print(("PASS" if ok else "FAIL"), "-", name, "" if ok else f"(exit {code}, got {got!r})")
        fails += not ok
    print(f"\n{len(CASES) - fails}/{len(CASES)} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
