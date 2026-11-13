# give-up-guard

[![CI](https://github.com/lucas-saldanha-werneck/give-up-guard/actions/workflows/test.yml/badge.svg)](https://github.com/lucas-saldanha-werneck/give-up-guard/actions/workflows/test.yml)
[![License](https://img.shields.io/github/license/lucas-saldanha-werneck/give-up-guard)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.3.6-blue)](CHANGELOG.md)

A Claude Code Stop hook that sends Claude back to work once when it ends a turn without checking
something it could have checked.

[![give-up-guard demo: tap to open the video](https://github.com/user-attachments/assets/32918ebb-33bb-4127-89c0-84bb1de5be8f)](https://lucas-saldanha-werneck.github.io/give-up-guard/demo.mp4)

<table>
<tr>
<td align="center"><img src="https://github.com/user-attachments/assets/c8f3f57f-5768-4ac1-987b-8a06989a24c1" alt="Claude says what it did not check" width="320"><br>Claude says what it did not check</td>
<td align="center"><img src="https://github.com/user-attachments/assets/74c6ea88-9d82-4e77-878f-5654625c8b75" alt="The hook sends it back once" width="320"><br>The hook sends it back once</td>
<td align="center"><img src="https://github.com/user-attachments/assets/25575501-0ce4-435f-9868-e4aeb99ea38a" alt="Claude checks before it gives up" width="320"><br>Claude checks before it gives up</td>
</tr>
</table>

Models often stop early. They write "Not checked: the deploy log" when reading the log takes one
command, or "you'll need to do this by hand" when a CLI could do it. A rule in `CLAUDE.md` helps,
but the model still slips. A Stop hook catches the slip as it happens.

The hook blocks the stop when the final answer does one of these things:

1. It hands the task back to you ("I can't upload it", "you'll need to click...") without listing
   the routes it tried. Steps only a human can do (captcha, 2FA, payment, QR code, biometrics,
   Touch ID, Face ID, reviewing or approving a draft before it goes out) are let through.
2. It says a command, option or feature doesn't exist without saying where it looked.
3. It asks you for data (email, login, username...) without saying where it looked first. The
   hook tells Claude to look in project files, notes, config and its tools. Asking you for a
   secret (password, token, API key, PIN) is let through by default, so the hook never pushes
   Claude to go and fetch a credential on its own (a sentence that asks for a secret is let through
   by rules 1 and 2 as well). Set `GIVE_UP_GUARD_SECRETS=1` to check those asks too.
4. It lists something as not checked without saying why it can't be checked now. "You asked me not
   to run it" counts as a reason.

## What Claude sees

Claude ends its turn with `Done. Not checked: whether the migration ran.` The hook blocks the stop,
and Claude gets this message and keeps working:

```
Stop hook feedback:
You listed something as not checked. Check now whatever you can with the tools you have (open the file, run the command, read the real state). Keep on the list only what is impossible to check right now, and say why for each item. If the user told you not to run or touch something, respect that: do not run it, keep it on the list and say the user asked you not to. (give-up-guard: verify before you claim)
```

In a test run, Claude then searched for the migration files and rewrote the answer to say where it
had looked and what it still could not confirm.

## Examples

- Claude ends with `Done. Not checked: whether the migration ran.` The stop is blocked once and Claude goes to check (see above).
- Claude ends with "you'll need to click upload yourself" and no routes tried: the stop is blocked once and Claude is told to try its tools first.
- Claude ends with "I can't approve the draft for you" or a captcha step: it passes, because only a human can do those.

## Install

```
/plugin marketplace add lucas-saldanha-werneck/lucas-tools
/plugin install give-up-guard@lucas-tools
```

It needs `python3` (3.8 or newer) on your `PATH`. There are no other dependencies.

## Languages and patterns

The plugin ships patterns for English (`patterns/en.json`) and Portuguese (`patterns/pt.json`). The
hook loads and merges every `*.json` file in these folders:

- the plugin's `patterns/` folder
- each folder listed in `GIVE_UP_GUARD_PATTERNS` (separated by `:`, or `;` on Windows; absolute or
  starting with `~`, a relative folder is ignored)
- `~/.config/give-up-guard/patterns/` (or `$XDG_CONFIG_HOME/give-up-guard/patterns/` when `XDG_CONFIG_HOME` is set)

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
| `human_only` | a step only a human can do, such as a captcha or approving a draft (cancels rule 1) |
| `not_exists` | says something doesn't exist |
| `searched` | says where it didn't find it (cancels rule 2) |
| `asks_data` | asks the user for an email, login, token... |
| `secret` | the data asked for is a secret (rules 1 to 3 skip a sentence that asks for one unless `secrets` is on, see below) |
| `not_checked` | lists something as not checked |
| `why_not` | gives a reason it can't be checked (cancels rule 4) |

The hook lowercases the text and strips accents before matching, so write `nao`, not `não`. A file
that isn't a valid JSON object, or a pattern that isn't a valid regular expression, is skipped, and
the other patterns still apply.

## Settings

Your own settings live outside the plugin, in a folder that plugin updates never touch:

- `~/.config/give-up-guard/config.json` (or `$XDG_CONFIG_HOME/give-up-guard/config.json` when
  `XDG_CONFIG_HOME` is set; on Windows `~` is your user folder, `%USERPROFILE%`)
- or any file named by `GIVE_UP_GUARD_CONFIG`
- your extra patterns go in `patterns/` in the same folder (see above)

You don't have to create the file: the plugin writes it the first time a session starts (or the
first time the hook runs), from [`config.example.json`](config.example.json), with every key at
its default and a one-line note per key under `_doc`. That file behaves exactly like having no
file: `secrets` and `headless` start as `null`, which means "use the `/config` option". Plugin
updates never touch it, and an existing file is never overwritten, so edit it freely.

Every key is optional. A missing or broken file means the defaults.

```json
{
  "secrets": true,
  "headless": false,
  "reason_suffix": "Tools you have: my-search-cli, the team wiki, `pass` for secrets.",
  "reasons": {
    "asks_data": "Before asking me: grep the notes folder and the password manager. Then write 'Searched in: ...'."
  }
}
```

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `secrets` | true/false/null | null (the `/config` option, off by default) | also block asks for a password, token or key. Claude is then told to look in the environment, a secrets file or a password manager it was given access to, if the task allows it, and never to print the secret |
| `headless` | true/false/null | null (the `/config` option, off by default) | also check `claude -p` runs, which are skipped by default |
| `reasons` | object | built-in texts | replaces the text Claude sees for a rule. Keys: `give_up`, `not_exists`, `asks_data`, `asks_secret`, `not_checked`. Use it to name the tools Claude should try, in your language |
| `reason_suffix` | string | none | appended to every reason, built-in or yours |

The two switches can also be set without the file:

| Where | Example | Wins over |
| --- | --- | --- |
| environment variable | `GIVE_UP_GUARD_SECRETS=1`, `GIVE_UP_GUARD_HEADLESS=0` (`1` on, `0` off) | the file and `/config` |
| `config.json` | `"secrets": true` | `/config` |
| `/config` in Claude Code | *Also block asks for secrets*, *Also check claude -p runs* (stored by Claude Code in your `settings.json`, as `pluginConfigs`) | nothing |

Other environment variables:

| Variable | Effect |
| --- | --- |
| `GIVE_UP_GUARD_PATTERNS` | extra pattern folders, as above |
| `GIVE_UP_GUARD_CONFIG` | path of the settings file, instead of the default above (absolute or starting with `~`; a relative path is ignored, so a project folder cannot bring its own settings) |

## How it works

When Claude tries to stop, the hook reads the final answer (`last_assistant_message`, or the last
assistant text in the transcript if that field is missing). It removes fenced code blocks (three or
more backticks or tildes, including a fence left open at the end), then text inside double quotes, curly double quotes and
backticks, so quoting a phrase or an example doesn't count. A straight double quote right after a
letter or digit (an inch mark, as in `27"`) does not start a quote. It then checks the four rules
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
/plugin uninstall give-up-guard@lucas-tools
```

## Limits

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

## Security

See [SECURITY.md](SECURITY.md) for what this plugin accesses and how to report a vulnerability.
