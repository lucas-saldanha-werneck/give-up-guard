# give-up-guard

A Claude Code Stop hook that sends Claude back to work when it ends a turn without having checked
what it could have checked.

## What it does

When Claude tries to end its turn, the hook reads the final answer. It blocks the stop once, and
tells Claude what to do instead, when the answer:

1. **Hands the task back to you** ("I can't upload it", "you'll need to click...") without a
   `Routes tried:` line, and the step isn't one only a human can do (captcha, 2FA, payment,
   biometrics, QR code).
2. **Says a tool, command or option doesn't exist** without saying where it looked.
3. **Asks you for data** (email, login, token...) without saying where it looked first.
4. **Lists something as not checked** without saying why it can't be checked right now.

The rule behind all four: verify before you claim. Keep in the answer only what is really
impossible, and say why.

## Why

Models often stop early: "Not checked: the deploy log" when reading the log takes one command, or
"you'll need to do this by hand" when there is a CLI for it. A rule in `CLAUDE.md` helps, but the
model still slips. A Stop hook catches it at the moment it happens.

## What Claude sees

The answer ends with `Not checked: whether the migration ran.` The hook blocks the stop and Claude
gets:

> You listed something as not checked. Check now whatever you can with the tools you have (open the
> file, run the command, read the real state). Keep on the list only what is impossible to check
> right now, and say why for each item. (give-up-guard: verify before you claim)

Claude then runs the check and rewrites the answer.

## Safety

- **Blocks at most once in a row.** When Claude is already continuing because of a Stop hook
  (`stop_hook_active`), the hook does nothing, so it can never loop.
- **Fails silently.** Any error (bad input, unreadable transcript, broken pattern) means no block.
- **Skips headless runs** (`claude -p`), where no one reads the answer and an extra turn would only
  spoil the output a script reads. Set `GIVE_UP_GUARD_HEADLESS=1` to check them too.
- Text inside quotes or backticks is ignored, so quoting a phrase isn't a give-up.

## Install

```
/plugin marketplace add lucas-saldanha-werneck/give-up-guard
/plugin install give-up-guard@give-up-guard
```

Requires `python3` (3.8+) on `PATH`. No other dependencies.

## Config: languages and patterns

Patterns ship for English (`patterns/en.json`) and Portuguese (`patterns/pt.json`). Every `*.json`
file in these folders is loaded and merged:

- the plugin's `patterns/` folder
- folders listed in `GIVE_UP_GUARD_PATTERNS` (separated by `:`; `;` on Windows)
- `~/.config/give-up-guard/patterns/`

To add a language or a phrase, drop a file in `~/.config/give-up-guard/patterns/`, for example
`es.json`:

```json
{
  "not_checked": ["no (verifique|comprobe|probe)"],
  "why_not": ["imposible", "sin acceso"]
}
```

Keys (all optional; each is a list of Python regular expressions, OR-ed together):

| Key | Meaning |
| --- | --- |
| `give_up` | handing the task back to the user |
| `tried` | the answer lists routes tried (cancels rules 1-3) |
| `human_only` | a step only a human can do (cancels rule 1) |
| `not_exists` | claims something doesn't exist |
| `searched` | says where it didn't find it (cancels rule 2) |
| `asks_data` | asks the user for an email, login, token... |
| `not_checked` | lists something as not checked |
| `why_not` | gives a reason it can't be checked (cancels rule 4) |

Text is lowercased and accents are stripped before matching, so write `nao`, not `não`.

## Test

```
python3 tests/test_give_up_guard.py
```

## Optional requirements

None.

## Uninstall

```
/plugin uninstall give-up-guard@give-up-guard
```

## License

MIT

Built with Claude Code
