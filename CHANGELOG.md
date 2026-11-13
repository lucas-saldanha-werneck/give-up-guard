# Changelog

All notable changes to this plugin. Versions follow `.claude-plugin/plugin.json`.

## 0.3.6 (2026-11-13)

- Add an Examples section to the README.

## 0.3.5 (2026-11-12)

- A check the user said not to run is a valid reason; reviewing or approving a draft counts as a human step.
- Read the transcript as UTF-8 whatever the locale; read config.json with a BOM.
- `GIVE_UP_GUARD_PATTERNS`: expand `~`, ignore relative folders; straight quotes used as inch marks no longer hide text.

## 0.3.4 (2026-11-11)

- Let secret asks through the give-up and not-exists rules too.

## 0.3.3 (2026-11-11)

- Point to the catalog repo's new name, `lucas-tools`.

## 0.3.2 (2026-11-11)

- Catalog renamed to `lucas-tools`.

## 0.3.1 (2026-11-09)

- One-line description, catalog install steps, heading names.

## 0.3.0 (2026-11-08)

- Settings file with switches, custom reason texts and an XDG config folder; created on first run from `config.example.json`.
- Skip a relative config path; expand `~`; leave skipped `claude -p` runs alone.

## 0.2.0 (2026-11-08)

- Let secret asks through by default; ignore fenced code.
- CI runs the tests on Linux, macOS and Windows.

## 0.1.1 (2026-11-08)

- Scope exemptions to their claim; isolate bad patterns.

## 0.1.0 (2026-11-08)

- First release: a Stop hook that makes Claude verify before it claims.
