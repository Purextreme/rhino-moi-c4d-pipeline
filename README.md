# Rhino → MoI → Cinema 4D Pipeline Skill

A Codex Skill for the guarded Rhino 7 → Rhino 5 → MoI FBX → Cinema 4D handoff. It exports Rhino metadata read-only, preserves geometry through MoI, and reconstructs Rhino Layer or Block hierarchy in Cinema 4D from verified spatial evidence.

## What is included

- The complete orchestration instructions and validation gates.
- A bundled Rhino metadata exporter based on Rhino COM and Rhino IronPython.
- Reusable Cinema 4D scene probes and equal-count Layer reconstruction logic.
- References for MoI export, matching, recovery, artifact consolidation, and acceptance.
- A maintainer-reviewed improvement queue for lessons learned from verified real runs.

The general-purpose [`c4d-remote-executor`](https://github.com/Purextreme/C4D_remote_script_bridge) Skill remains an external required dependency. Every Cinema 4D probe, mutation, recovery inspection, preview, and verification pass must run through it.

## Repository layout

```text
rhino-moi-c4d-pipeline/
├── SKILL.md
├── agents/
├── improvements/
├── references/
└── scripts/
```

The inner `rhino-moi-c4d-pipeline/` directory is the installable Skill. Repository-level files are intentionally kept outside that directory.

## Install

Ask Codex to install the Skill from:

```text
https://github.com/Purextreme/rhino-moi-c4d-pipeline/tree/main/rhino-moi-c4d-pipeline
```

Using the bundled installer directly:

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py" `
  --repo Purextreme/rhino-moi-c4d-pipeline `
  --path rhino-moi-c4d-pipeline
```

Restart Codex after installation so the new Skill is discovered.

## Scope

Use this Skill for complete Rhino → MoI → C4D reconstruction. Use `c4d-remote-executor` directly for ordinary C4D-only work.

The workflow deliberately refuses ambiguous reconstruction. Every model is probed again; object order, generated names, axis mapping, counts, and matching thresholds are never inherited as identity from an earlier run.
