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

Claude Code asks for the setting `designer_address`. See the next section.

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

## Limits

- Claude Code does not load skills from MCP servers yet. For this reason, the plugin has its own copy of the skill.
- The skill copy is generated from `skills/d3-designer` in `disguise-one/d3`. Do not edit it here.
- This repository is private until release.
