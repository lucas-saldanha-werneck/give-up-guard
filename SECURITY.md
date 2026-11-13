# Security policy

## Reporting a vulnerability

Please report security problems privately: open the **Security** tab of this repository and choose
**Report a vulnerability** (GitHub private vulnerability reporting). Please do not open a public issue
for a security problem. You will get an answer in the same thread.

## Supported versions

Only the latest release is supported. Fixes land in a new release; older versions are not patched.

## What this plugin accesses

- **Files it reads:** the transcript of the current session (to find Claude's last reply), its pattern files, and its settings file `~/.config/give-up-guard/config.json`.
- **Files it writes:** only that settings file, created once from `config.example.json` with mode `0600` when it is missing.
- **Network:** none. It is a local Python hook (a Stop hook) and starts no other program.
- **Secrets:** it never reads or prints them. Its text to Claude says to look for a secret the user already gave access to and never print it.
