# CLAUDE.md

This is the Claude Code plugin `disguise-designer` (marketplace `disguise`).
It has the MCP server `designer` (`.mcp.json`) and the skill `d3-designer` (`skills/`).

## Generated files

- `skills/` and `skills-manifest.json` are generated. Never edit them by hand.
- The source is `skills/d3-designer` in the private repository `disguise-one/d3`. Change it there.
- `scripts/sync_skill.py` copies the skill. It removes the `allowed-tools` line from `SKILL.md`.
  Tools of a plugin server have the name `mcp__plugin_disguise-designer_designer__<tool>`.
  The d3 value does not match them.
- `.github/workflows/release.yml` runs the sync for each Designer release.
- `scripts/verify_against_d3service.py` compares the copy with a running d3service.

## Commands

```bash
python scripts/sync_skill.py --d3 <path-to-d3-checkout>
python scripts/sync_skill.py --check
python -m unittest discover -s scripts
claude plugin validate .
```

- Run the unit tests and `claude plugin validate .` before you open a PR.

## Versioning

- The version is the Designer release number.
- On each release, change `version` in `.claude-plugin/plugin.json`. If you do not, users do not get the update.
- Never rename the plugin. A new name is a new plugin. Users lose their install.

## Branches

- Work on a branch. Open a PR.
- Do not push directly to `main`.

## Style

- Write docs and comments in plain, short sentences.
- Use one idea in each sentence.
