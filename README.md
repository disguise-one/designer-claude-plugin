# disguise-designer

A Claude Code plugin for disguise Designer.

One install gives you two things:

- The Designer MCP server. Its name is `designer`. It lets Claude Code use the tools of a running Designer.
- The skill `d3-designer`. It teaches Claude how to work with Designer.

## Install

```bash
claude plugin marketplace add disguise-one/designer-claude-plugin
claude plugin install disguise-designer@disguise
```

Claude Code asks for the setting `designer_address`. See the next section. In a script, give it with the install command:

```bash
claude plugin install disguise-designer@disguise --config designer_address=192.168.1.20
```

## Designer address

`designer_address` is the host name or IP address of the machine that runs Designer. You can add a port. The default is `localhost`.

The plugin connects to `http://<designer_address>/api/mcp/rpc`.

| Where Claude runs | designer_address |
|---|---|
| Windows (same machine as Designer) | `localhost` |
| WSL on the Designer machine | `host.docker.internal` |
| Cowork | `host.docker.internal` |

- Do not use `localhost` in WSL or Cowork. It points to the WSL guest or the VM, not to Designer.
- The web port is 80. Port 80 needs no port in the address.
- The internal service port is 12302. To use it, write `localhost:12302`.
- If Designer uses a different port, write that port in the address.

## Update

```bash
claude plugin update disguise-designer@disguise
```

Auto-update is off by default. To turn it on, open `/plugin` in Claude Code and go to Marketplaces.

### Pin a release

Each release has a git tag, `disguise-designer--v<version>`. To stay on one release, add the marketplace at its tag:

```bash
claude plugin marketplace add disguise-one/designer-claude-plugin#disguise-designer--v34.0.0
claude plugin install disguise-designer@disguise
```

A marketplace that you add at a tag does not move to a later release. To change release, remove the marketplace and add it again at the new tag.

## What the skill gives

The skill `d3-designer` teaches Claude to automate Designer projects. It uses the Designer MCP tools and the in-project Python plugin API.

It covers:

- project and session control, transports and timeline
- layers, effect modules, content and media
- stage and projection mapping, camera calibration
- devices (DMX, MIDI, serial, OSC) and multi-machine networking
- RenderStream, audio, colour, tracking, feeds and outputs

## Safety

- Do not connect an assistant to a machine that runs a live show.
- The Designer MCP server has no login. Each client that can reach it can use it.
- Read the security overview: https://help.disguise.one/designer/networking/security-overview
- Use a client that asks before it runs a tool.
- Save your project. Keep a backup.

## Releases

The plugin version is the Designer release number. For example, Designer release `r34.0.1` gives plugin version `34.0.1`.

A release takes these steps:

1. The `release` workflow starts. A person starts it by hand today. Designer CI starts it when a Designer release is finished (see `docs/designer-ci-hook.md`; not applied yet). Its inputs are the version and the `d3` ref (a branch, tag or commit of `disguise-one/d3`).
2. The workflow copies `skills/d3-designer` from that `d3` ref, removes the `allowed-tools` line, writes `skills-manifest.json` and sets `version` in `.claude-plugin/plugin.json`.
3. The workflow runs the unit tests, the manifest check and `claude plugin validate`.
4. The workflow opens a pull request named `Release <version>: sync d3-designer skill`. A person reads it and merges it with a merge commit.
5. The `tag` workflow runs when `plugin.json` changes on `main`. It makes and pushes the tag `disguise-designer--v<version>`. A person can also start it by hand.

To make a release by hand, run this in a clone of the repository:

```bash
gh workflow run release.yml -f version=34.0.1 -f d3_ref=release/r34.0.1
```

The release workflow needs these secrets: `D3_APP_ID` and `D3_APP_PRIVATE_KEY`. They belong to a GitHub App that can read `disguise-one/d3` and nothing else.

Users get a release only when `version` changes. Never change the plugin `name`.

## Limits

- Claude Code does not load skills from MCP servers yet. For this reason, the plugin has its own copy of the skill.
- The skill copy is generated from `skills/d3-designer` in `disguise-one/d3`. Do not edit it here.
- This repository is private until release.
