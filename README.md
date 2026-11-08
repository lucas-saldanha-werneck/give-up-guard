# give-up-guard

A Claude Code Stop hook that sends Claude back to work once when it ends a turn without checking
something it could have checked.

Models often stop early. They write "Not checked: the deploy log" when reading the log takes one
command, or "you'll need to do this by hand" when a CLI could do it. A rule in `CLAUDE.md` helps,
but the model still slips. A Stop hook catches the slip as it happens.

The hook blocks the stop when the final answer does one of these things:

1. It hands the task back to you ("I can't upload it", "you'll need to click...") without listing
   the routes it tried. Steps only a human can do (captcha, 2FA, payment, QR code, biometrics,
   Touch ID, Face ID) are let through.
2. It says a command, option or feature doesn't exist without saying where it looked.
3. It asks you for data (email, login, username...) without saying where it looked first. The
   hook tells Claude to look in project files, notes, config and its tools. Asking you for a
   secret (password, token, API key, PIN) is let through by default, so the hook never pushes
   Claude to go and fetch a credential on its own. Set `GIVE_UP_GUARD_SECRETS=1` to check those
   asks too.
4. It lists something as not checked without saying why it can't be checked now.

## What Claude sees

Claude ends its turn with `Done. Not checked: whether the migration ran.` The hook blocks the stop,
and Claude gets this message and keeps working:

```
Stop hook feedback:
You listed something as not checked. Check now whatever you can with the tools you have (open the file, run the command, read the real state). Keep on the list only what is impossible to check right now, and say why for each item. (give-up-guard: verify before you claim)
```

In a test run, Claude then searched for the migration files and rewrote the answer to say where it
had looked and what it still could not confirm.

## Install

```
/plugin marketplace add lucas-saldanha-werneck/give-up-guard
/plugin install give-up-guard@give-up-guard
```

It needs `python3` (3.8 or newer) on your `PATH`. There are no other dependencies.

## Config: languages and patterns

The plugin ships patterns for English (`patterns/en.json`) and Portuguese (`patterns/pt.json`). The
hook loads and merges every `*.json` file in these folders:

- the plugin's `patterns/` folder
- each folder listed in `GIVE_UP_GUARD_PATTERNS` (separated by `:`, or `;` on Windows)
- `~/.config/give-up-guard/patterns/`

To add a language or a phrase, put a file in `~/.config/give-up-guard/patterns/`. For example,
`es.json`:

```json
{
  "not_checked": ["no (verifique|comprobe|probe)"],
  "why_not": ["imposible", "sin acceso"]
}
```

Every key is optional. Each one is a list of Python regular expressions (a single string counts as
a list of one), and a match on any of them counts. Each pattern is matched on its own, so inline
flags like `(?i)` work.

| Key | Meaning |
| --- | --- |
| `give_up` | hands the task back to the user |
| `tried` | the answer lists routes tried or places searched (cancels rules 1 to 3) |
| `human_only` | a step only a human can do (cancels rule 1) |
| `not_exists` | says something doesn't exist |
| `searched` | says where it didn't find it (cancels rule 2) |
| `asks_data` | asks the user for an email, login, token... |
| `secret` | the data asked for is a secret (rule 3 skips it unless `GIVE_UP_GUARD_SECRETS=1`) |
| `not_checked` | lists something as not checked |
| `why_not` | gives a reason it can't be checked (cancels rule 4) |

The hook lowercases the text and strips accents before matching, so write `nao`, not `não`. A file
that isn't a valid JSON object, or a pattern that isn't a valid regular expression, is skipped, and
the other patterns still apply.

Environment variables:

| Variable | Effect |
| --- | --- |
| `GIVE_UP_GUARD_PATTERNS` | extra pattern folders, as above |
| `GIVE_UP_GUARD_HEADLESS=1` | also check `claude -p` runs, which are skipped by default |
| `GIVE_UP_GUARD_SECRETS=1` | also block asks for a password, token or key. Claude is then told to look in the environment, a secrets file or a password manager it was given access to, if the task allows it, and never to print the secret |

## How it works

When Claude tries to stop, the hook reads the final answer (`last_assistant_message`, or the last
assistant text in the transcript if that field is missing). It removes fenced code blocks (three or
more backticks or tildes, including a fence left open at the end), then text inside double quotes, curly double quotes and
backticks, so quoting a phrase or an example doesn't count. It then checks the four rules
in order and returns `{"decision": "block", "reason": ...}` for the first one that matches.

A phrase that cancels a rule only counts near the claim it excuses: in the same sentence or line, or
the one right after. So "The build requires Python 3.8. Not checked: the deploy log." is blocked,
because "requires" explains something else. The exception is a line that starts with a label such as
`Routes tried:` or `Searched in:`, which covers the whole answer.

- It blocks at most once in a row. If Claude is already continuing because of a Stop hook
  (`stop_hook_active`), it does nothing, so it can't loop.
- Any error (bad input, unreadable transcript) means no block.
- It skips `claude -p` runs (`CLAUDE_CODE_ENTRYPOINT=sdk-cli`), where no one reads the answer and
  an extra turn would only change the output a script reads.

To run the tests:

```
python3 tests/test_give_up_guard.py
```

## Uninstall

```
/plugin uninstall give-up-guard@give-up-guard
```

## Limits and what was not tested

- It matches phrases, so it misses give-ups worded in ways the patterns don't cover, and it can
  block an answer that only looks like one. Add or narrow patterns in your own folder.
- For a list under a heading like `Not checked:`, a reason in the first item also covers the
  heading, so the other items are not checked one by one.
- Tested on macOS in the terminal, including a real session where the hook blocked a stop. Not
  tested on Linux or Windows. On Windows the hook runs `python3`, which may not be on `PATH` there.
- Not tested in the desktop app or the IDE extensions. The Claude Code docs say hooks fire there too.
- Only `claude -p` runs are skipped. Agent SDK runs from TypeScript or Python are checked like
  normal sessions.

## License

MIT

Built with Claude Code
