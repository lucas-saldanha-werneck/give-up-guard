#!/usr/bin/env python3
"""Feeds sample Stop-hook JSON to the hook and checks whether it blocks."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "give_up_guard.py")


def run(payload, env_extra=None):
    env = seed_env(**(env_extra or {}))  # no user patterns or settings
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
    # tapping an answer option is the user's decision, not a task handed back
    ("pt toque na opcao is a decision", msg("Toque na opção que preferir."), None, None),
    ("pt clique em Sim is a decision", msg("Para seguir, clique em Sim no botão abaixo."), None, None),
    ("pt toque em app step still blocked", msg("Toque em Settings e depois em Privacy."), None, "Before handing this task back"),
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
    # an exemption only counts near the claim it excuses
    ("why_not elsewhere doesn't excuse", msg("The build requires Python 3.8. Not checked: the production deploy log."),
     None, "You listed something as not checked"),
    ("tried elsewhere doesn't excuse", msg("I searched for the README. I cannot upload the artifact."),
     None, "Before handing this task back"),
    ("why_not in next sentence", msg("Not checked: the deploy log. Only you can open that dashboard."), None, None),
    ("tried label line anywhere", msg("Routes tried: API (403), CLI (missing).\n\nSo I can't upload the file. "
                                      "You'll need to open the site."), None, None),
    ("searched label line anywhere", msg("- Searched in: the config, the .env\n\nSome notes.\n\nWhat is your email?"),
     None, None),
    # asking for a secret is not a cue to go and fetch it (opt in with GIVE_UP_GUARD_SECRETS=1)
    ("en asks password let through", msg("What is your password for the dashboard?"), None, None),
    ("en asks api key let through", msg("Can you share the API key?"), None, None),
    ("pt asks senha let through", msg("Me passa a senha do painel."), None, None),
    ("secret asks opt-in", msg("What is your password for the dashboard?"), {"GIVE_UP_GUARD_SECRETS": "1"},
     "Before asking the user for this secret"),
    ("non-secret ask still blocked", msg("What is your username on the server?"), None, "Before asking the user for this data"),
    # fenced code blocks are quotes too
    ("backtick fence ignored", msg("Example final answer:\n\n```\nDone.\nNot checked: the deploy log.\n```\n"), None, None),
    ("tilde fence ignored", msg("Example:\n~~~text\nI can't upload the file. You'll need to open the site.\n~~~"), None, None),
    ("long fence with inner fence ignored", msg("Example:\n````md\n```\nx\n```\nNot tested yet.\n````\nDone."), None, None),
    ("unclosed fence ignored", msg("Example:\n```\nNot checked: the deploy log."), None, None),
    ("text after a fence still counts", msg("```\nexample\n```\nNot checked: the deploy log."), None, "You listed"),
]


EXAMPLE = os.path.join(os.path.dirname(HOOK), "..", "config.example.json")


def read(path):
    with open(path, "rb") as f:
        return f.read()


def seed_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_ENTRYPOINT", "XDG_CONFIG_HOME")
           and not k.startswith(("GIVE_UP_GUARD_", "CLAUDE_PLUGIN_OPTION_"))}
    env["HOME"] = env["USERPROFILE"] = tempfile.mkdtemp()
    env.update(extra)
    return env


def seed(env, args=("--seed",), payload=""):
    return subprocess.run([sys.executable, HOOK, *args], input=payload, capture_output=True, text=True, env=env)


def seed_checks():
    """The plugin creates <config dir>/config.json by itself on first run (installing runs no hook)."""
    results = []

    def check(name, ok, detail=""):
        print(("PASS" if ok else "FAIL"), "-", name, "" if ok else f"({detail})")
        results.append(bool(ok))

    example = json.loads(read(EXAMPLE))
    check("starter has a doc line per key", set(example["_doc"]) - {"about"} == {k for k in example if k[0] != "_"})
    check("starter switches defer to /config", example["secrets"] is None and example["headless"] is None)
    with open(os.path.join(os.path.dirname(HOOK), "..", ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
        ss = json.load(f)["hooks"].get("SessionStart", [])
    check("SessionStart hook registered", any("--seed" in h.get("args", []) for g in ss for h in g["hooks"]))

    # missing -> created with the starter, silently; ~/.config, XDG_CONFIG_HOME and GIVE_UP_GUARD_CONFIG respected
    env = seed_env()
    r = seed(env)
    made = os.path.join(env["HOME"], ".config", "give-up-guard", "config.json")
    check("seed creates ~/.config/give-up-guard/config.json", os.path.exists(made) and read(made) == read(EXAMPLE),
          r.stderr)
    check("seed is silent, exit 0", (r.returncode, r.stdout, r.stderr) == (0, "", ""),
          repr((r.returncode, r.stdout, r.stderr)))
    xdg = tempfile.mkdtemp()
    env = seed_env(XDG_CONFIG_HOME=xdg)
    seed(env)
    check("seed respects XDG_CONFIG_HOME", read(os.path.join(xdg, "give-up-guard", "config.json")) == read(EXAMPLE)
          and not os.path.exists(os.path.join(env["HOME"], ".config")))
    cfile = os.path.join(tempfile.mkdtemp(), "new", "mine.json")
    seed(seed_env(GIVE_UP_GUARD_CONFIG=cfile))
    check("seed respects GIVE_UP_GUARD_CONFIG", os.path.exists(cfile) and read(cfile) == read(EXAMPLE))
    env = seed_env()
    seed(env, args=(), payload=json.dumps(msg("Done.")))
    made = os.path.join(env["HOME"], ".config", "give-up-guard", "config.json")
    check("the Stop hook seeds too (first use)", os.path.exists(made) and read(made) == read(EXAMPLE))

    proj = tempfile.mkdtemp()
    r = subprocess.run([sys.executable, HOOK, "--seed"], capture_output=True, text=True, cwd=proj,
                       env=seed_env(GIVE_UP_GUARD_CONFIG="rel-config.json"))
    check("relative GIVE_UP_GUARD_CONFIG is not seeded into the project", r.returncode == 0 and os.listdir(proj) == [])

    # a relative GIVE_UP_GUARD_CONFIG or XDG_CONFIG_HOME is not read from the project folder either
    proj = tempfile.mkdtemp()
    os.makedirs(os.path.join(proj, "give-up-guard"))
    for rel in ("rel-config.json", os.path.join("give-up-guard", "config.json")):
        with open(os.path.join(proj, rel), "w") as f:
            json.dump({"reasons": {"not_checked": "PLANTED"}}, f)
    for extra in ({"GIVE_UP_GUARD_CONFIG": "rel-config.json"}, {"XDG_CONFIG_HOME": "."}):
        p = subprocess.run([sys.executable, HOOK], input=json.dumps(msg("Not checked: the log.")), capture_output=True,
                           text=True, cwd=proj, env=seed_env(**extra))
        out = json.loads(p.stdout or "null")
        check(f"relative {list(extra)[0]} is not read from the project",
              bool(out) and out["reason"].startswith("You listed"), p.stdout)

    # ~ in GIVE_UP_GUARD_CONFIG (settings.json env is not expanded by a shell) is the home folder
    env = seed_env(GIVE_UP_GUARD_CONFIG="~/gug/mine.json")
    seed(env)
    made = os.path.join(env["HOME"], "gug", "mine.json")
    check("~ in GIVE_UP_GUARD_CONFIG: seeded in the home folder", os.path.exists(made))
    with open(made, "w") as f:
        json.dump({"secrets": True}, f)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(msg("What is your password for the dashboard?")),
                       capture_output=True, text=True, env=env)
    out = json.loads(p.stdout or "null")
    check("~ in GIVE_UP_GUARD_CONFIG: the file is read",
          bool(out) and out["reason"].startswith("Before asking the user"), p.stdout)

    # a skipped headless run (`claude -p`) creates nothing, from either hook
    env = seed_env(CLAUDE_CODE_ENTRYPOINT="sdk-cli")
    seed(env)
    seed(env, args=(), payload=json.dumps(msg("Done.")))
    check("headless run (skipped): nothing seeded", not os.path.exists(os.path.join(env["HOME"], ".config")))
    env = seed_env(CLAUDE_CODE_ENTRYPOINT="sdk-cli", CLAUDE_PLUGIN_OPTION_CHECK_HEADLESS="true")
    seed(env)
    check("headless run checked: seeded",
          os.path.exists(os.path.join(env["HOME"], ".config", "give-up-guard", "config.json")))

    # existing -> byte-identical, same mtime
    for body in (b'{"secrets": true}', b"{not json", b""):
        cdir = tempfile.mkdtemp()
        cfile = os.path.join(cdir, "give-up-guard", "config.json")
        os.makedirs(os.path.dirname(cfile))
        with open(cfile, "wb") as f:
            f.write(body)
        before = os.stat(cfile).st_mtime_ns
        env = seed_env(XDG_CONFIG_HOME=cdir)
        seed(env)
        seed(env, args=(), payload=json.dumps(msg("Not checked: the log.")))
        check(f"existing file untouched {body[:12]!r}", read(cfile) == body and os.stat(cfile).st_mtime_ns == before)

    # unwritable place -> no crash, no output, the guard still works
    blocker = os.path.join(tempfile.mkdtemp(), "a-file")
    with open(blocker, "w") as f:
        f.write("x")
    r = seed(seed_env(GIVE_UP_GUARD_CONFIG=os.path.join(blocker, "sub", "config.json")))  # parent is a file
    check("unwritable path: seed exit 0, silent", (r.returncode, r.stdout, r.stderr) == (0, "", ""))
    code, out = run(msg("Not checked: the log."), {"GIVE_UP_GUARD_CONFIG": os.path.join(blocker, "sub", "c.json")})
    check("unwritable path: the hook still works", code == 0 and out and out["reason"].startswith("You listed"))
    if os.name != "nt" and os.geteuid() != 0:  # read-only folder (root and Windows ignore the mode)
        ro = tempfile.mkdtemp()
        os.chmod(ro, 0o500)
        try:
            r = seed(seed_env(XDG_CONFIG_HOME=ro))
            check("read-only folder: exit 0, nothing written",
                  r.returncode == 0 and r.stderr == "" and os.listdir(ro) == [])
        finally:
            os.chmod(ro, 0o700)

    # the seeded file behaves like no file in every case, and /config options still win over it
    seeded = tempfile.mkdtemp()
    os.makedirs(os.path.join(seeded, "give-up-guard"))
    with open(os.path.join(seeded, "give-up-guard", "config.json"), "wb") as f:
        f.write(read(EXAMPLE))
    differ = []
    for name, payload, env, _ in CASES:
        if isinstance(payload, str) or (env and ("XDG_CONFIG_HOME" in env or "GIVE_UP_GUARD_CONFIG" in env)):
            continue  # cases that bring their own settings file
        no_file = dict(env or {}, GIVE_UP_GUARD_CONFIG=os.path.join(blocker, "no", "config.json"))  # can't be seeded
        if run(payload, no_file) != run(payload, dict(env or {}, XDG_CONFIG_HOME=seeded)):
            differ.append(name)
    check("seeded file gives the same result as no file in every case", not differ, differ)
    ask_pw, headless = msg("What is your password for the dashboard?"), {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}
    code, out = run(ask_pw, {"XDG_CONFIG_HOME": seeded, "CLAUDE_PLUGIN_OPTION_CHECK_SECRETS": "true"})
    check("/config secrets option still wins over the seeded file",
          bool(out) and out["reason"].startswith("Before asking the user for this secret"))
    code, out = run(msg("Not checked: anything."),
                    dict(headless, XDG_CONFIG_HOME=seeded, CLAUDE_PLUGIN_OPTION_CHECK_HEADLESS="true"))
    check("/config headless option still wins over the seeded file", bool(out) and out["reason"].startswith("You listed"))
    check("checks never changed the seeded file",
          read(os.path.join(seeded, "give-up-guard", "config.json")) == read(EXAMPLE))
    return len(results), results.count(False)


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
    # a bad custom file or pattern must not disable the bundled patterns
    def folder(name, content):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, name), "w") as f:
            f.write(content)
        return {"GIVE_UP_GUARD_PATTERNS": d}
    flags = folder("es.json", json.dumps({"not_checked": ["(?i)no comprobado"]}))
    CASES.append(("inline flag pattern keeps bundled", msg("Not checked: the log."), flags, "You listed"))
    CASES.append(("inline flag pattern works", msg("Listo. No comprobado el log."), flags, "You listed"))
    CASES.append(("json list file is skipped", msg("Not checked: the log."), folder("x.json", "[1, 2]"), "You listed"))
    CASES.append(("non-string pattern is skipped", msg("Not checked: the log."),
                  folder("x.json", json.dumps({"not_checked": [123], "why_not": [None]})), "You listed"))
    CASES.append(("string instead of list is one pattern", msg("Done. Ran the tests: 12 passed."),
                  folder("x.json", json.dumps({"not_checked": "no comprobado"})), None))

    # your settings: <config dir>/config.json (XDG_CONFIG_HOME respected) or GIVE_UP_GUARD_CONFIG
    def settings(cfg):
        base = tempfile.mkdtemp()
        os.makedirs(os.path.join(base, "give-up-guard"))
        with open(os.path.join(base, "give-up-guard", "config.json"), "w", encoding="utf-8") as f:
            f.write(cfg if isinstance(cfg, str) else json.dumps(cfg))
        return {"XDG_CONFIG_HOME": base}
    ask_pw, headless = msg("What is your password for the dashboard?"), {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}
    CASES.extend([
        ("config secrets on", ask_pw, settings({"secrets": True}), "Before asking the user for this secret"),
        ("env 0 beats config secrets", ask_pw, dict(settings({"secrets": True}), GIVE_UP_GUARD_SECRETS="0"), None),
        ("config headless on", msg("Not checked: anything."), dict(settings({"headless": True}), **headless), "You listed"),
        ("env 0 beats config headless", msg("Not checked: anything."),
         dict(settings({"headless": True}), GIVE_UP_GUARD_HEADLESS="0", **headless), None),
        ("plugin option secrets", ask_pw, {"CLAUDE_PLUGIN_OPTION_CHECK_SECRETS": "true"},
         "Before asking the user for this secret"),
        ("config false beats plugin option", ask_pw,
         dict(settings({"secrets": False}), CLAUDE_PLUGIN_OPTION_CHECK_SECRETS="true"), None),
        ("plugin option headless", msg("Not checked: anything."),
         dict(CLAUDE_PLUGIN_OPTION_CHECK_HEADLESS="true", **headless), "You listed"),
        ("custom reason replaces text", msg("Not checked: the log."),
         settings({"reasons": {"not_checked": "Check it with mytool first."}}), "Check it with mytool first."),
        ("reason suffix keeps the default text", msg("I can't upload the file. You'll need to open the site."),
         settings({"reason_suffix": "Try tool-x and tool-y."}), "Before handing this task back"),
        ("broken config file is ignored", msg("Not checked: the log."), settings("{not json"), "You listed"),
        ("config that isn't an object is ignored", ask_pw, settings("[true]"), None),
    ])
    pbase = tempfile.mkdtemp()
    os.makedirs(os.path.join(pbase, "give-up-guard", "patterns"))
    with open(os.path.join(pbase, "give-up-guard", "patterns", "es.json"), "w") as f:
        json.dump({"not_checked": ["no (verifique|comprobe)"]}, f)
    CASES.append(("XDG patterns folder", msg("Listo. No verifiqué el log."), {"XDG_CONFIG_HOME": pbase}, "You listed"))
    cfile = os.path.join(tempfile.mkdtemp(), "mine.json")
    with open(cfile, "w") as f:
        json.dump({"secrets": True}, f)
    CASES.append(("GIVE_UP_GUARD_CONFIG path", ask_pw, {"GIVE_UP_GUARD_CONFIG": cfile},
                  "Before asking the user for this secret"))
    code, out = run(msg("I can't upload the file. You'll need to open the site."), settings({"reason_suffix": "Try tool-x."}))
    ok = bool(out) and out["reason"].endswith("(give-up-guard: verify before you claim) Try tool-x.")
    print(("PASS" if ok else "FAIL"), "-", "suffix goes at the end", "" if ok else f"(got {out!r})")
    fails += not ok

    # the default data reason must not send Claude to a password manager
    code, out = run(msg("What is your email for the account?"))
    ok = code == 0 and out and "password manager" not in out["reason"]
    print(("PASS" if ok else "FAIL"), "-", "data reason doesn't mention a password manager", "" if ok else f"(got {out!r})")
    fails += not ok

    for name, payload, env, want in CASES:
        if isinstance(payload, str):
            p = subprocess.run([sys.executable, HOOK], input=payload, capture_output=True, text=True,
                               env=seed_env())  # never the real ~/.config or the developer's settings
            code, out = p.returncode, (p.stdout.strip() or None)
        else:
            code, out = run(payload, env)
        got = out.get("reason") if isinstance(out, dict) else out
        ok = code == 0 and ((want is None and got is None) or (want and got and got.startswith(want)
                                                               and out.get("decision") == "block"))
        print(("PASS" if ok else "FAIL"), "-", name, "" if ok else f"(exit {code}, got {got!r})")
        fails += not ok
    n_seed, seed_fails = seed_checks()
    fails += seed_fails
    print(f"\n{len(CASES) + 2 + n_seed - fails}/{len(CASES) + 2 + n_seed} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
