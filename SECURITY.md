# Security policy

## Reporting a vulnerability

Please report security problems privately: open the **Security** tab of this repository and choose
**Report a vulnerability** (GitHub private vulnerability reporting). Please do not open a public issue
for a security problem. You will get an answer in the same thread.

## Supported versions

Only the latest release is supported. Fixes land in a new release; older versions are not patched.

## What this plugin accesses

- **What it does:** a Stop hook that can block Claude from ending its turn, once in a row, and sends Claude an instruction to check before it answers. A SessionStart hook only creates the settings file. Headless `claude -p` runs are skipped unless you turn them on.
- **Files it reads:** Claude's last reply (from the hook input, or from the current session's transcript file when the input lacks it), its pattern files plus any in `GIVE_UP_GUARD_PATTERNS` or `~/.config/give-up-guard/patterns/`, and its settings file `~/.config/give-up-guard/config.json` (or `$XDG_CONFIG_HOME/give-up-guard/`, or the path in `GIVE_UP_GUARD_CONFIG`).
- **Files it writes:** only that settings file, created once from `config.example.json` with mode `0600` when it is missing.
- **Network:** none. It is a local Python hook and starts no other program.
- **Secrets:** it never reads or prints them. Its text to Claude says to look for a secret the user already gave access to and never print it.
