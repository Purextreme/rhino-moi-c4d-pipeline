---
name: rhino-moi-c4d-pipeline
description: Run the complete Rhino 7 to Rhino 5 to MoI FBX to Cinema 4D handoff, including bundled Rhino metadata export and metadata-driven Layer or Block hierarchy reconstruction. Requires the external c4d-remote-executor Skill. Use for end-to-end Rhino to MoI to C4D reconstruction, not for ordinary C4D-only edits.
---

# Rhino to MoI to C4D Pipeline

Complete the geometry and hierarchy handoff while preserving the open source documents and refusing ambiguous reconstruction.

Read [references/workflow.md](references/workflow.md) before operating the applications. It contains the required MoI settings, mode selection, validation gates, and recovery rules. Before exporting Rhino metadata, also read [references/rhino-metadata-export.md](references/rhino-metadata-export.md).

## Required capabilities

- The Rhino metadata exporter is an internal component under `scripts/rhino-metadata/`; do not look for, invoke, or recreate a separate `rhino-metadata-export` Skill.
- At the start of every run, load and follow the external `c4d-remote-executor` Skill. It is a mandatory dependency because it owns C4D SDK guidance, protected mutation, recovery inspection, and verification. If it is unavailable, stop and report the missing dependency.
- Use the bundled Rhino metadata component for the active Rhino 7 snapshot and its process/document safety checks. It uses Rhino COM and is not a Rhino plug-in; the user does not run ScriptEditor manually.
- Use `c4d-remote-executor` for every C4D probe, protected mutation, recovery inspection, preview, and independent verification pass.
- Reuse the scripts under `scripts/c4d/` when their documented preconditions match the current scene. They are pipeline components, not a replacement for `c4d-remote-executor`; inject case paths and thresholds, inspect the script, and send it through the external Skill.
- Prefer application scripting. Use computer control only for MoI or file dialogs that do not expose a reliable local automation API.

## Non-negotiable invariants

- Require exactly one Rhino process and identify the active Rhino document before any export.
- Export metadata before any optional block explosion. Never decide from the viewport alone whether `ExplodeBlock` is needed.
- Do not modify or overwrite the active Rhino source. Export the same in-memory state as the metadata, preserve its original identity and modified state, and prepare any Block expansion in a separate copy. Read [references/rhino-working-copy.md](references/rhino-working-copy.md) when preparing that copy.
- Treat ASCII staging as temporary. After verification, consolidate the Rhino 5 and FBX artifacts into a source-side `codex_export_fbx` folder, verify collisions by hash, and remove the empty staging directory.
- Do not use C4D `obj*` names or object order as identity.
- Re-probe every model. Axis mapping, object counts, matching thresholds, and hierarchy mode are evidence, not constants inherited from a prior run.
- Preserve every C4D polygon world matrix across reparenting with `GetMg()` and `SetMg()`.
- Protect C4D mutations with the Remote Executor backup and an Undo transaction.
- If a C4D script fails after its first side effect, treat completion as unknown. Do not retry until a read-only probe establishes the actual document state.
- Stop before mutation on unresolved count differences, ambiguous assignments, excessive BBox error, missing Normal tags, or a changed active document.
- Treat success as requiring both bridge and script success: inspect top-level `ok`, `execution_ok`, and `verification_ok`, plus `result.execution_ok` and `result.verification_ok`. Require assertions where practical and a separate read-only verification pass; a zero client exit code alone is insufficient.

## Improvement queue

When the user requests experience capture or Skill maintenance, record or absorb only reusable lessons supported by a concrete error, warning, command, or verified artifact. Ordinary model handoffs do not require an experience file; respect the user's instructions about persistent records.

Before recording, read only [improvements/RULES.md](improvements/RULES.md). Do not list, search, or read existing pending entries. Do not modify another candidate or promote a candidate into established instructions, references, or scripts unless the maintainer explicitly requests review or absorption.

Experience logging must not interrupt recovery or delay the user's primary task. If requested recording is unavailable or unwritable, report that limitation instead of redirecting the entry to an unrelated path.

## Reconstruction modes

- If live top-level Rhino instance references exist, expand Block occurrences and reconstruct the Block tree.
- If the export is already exploded, reconstruct the Rhino Layer tree.
- If Rhino geometry and C4D polygon counts are equal, solve a global BBox assignment and reject ambiguity.
- If C4D contains extra polygons, test whether MoI split Rhino Breps by face material. First assign every Rhino Brep one-to-one, then attach only the leftover meshes that are spatially contained by a matched Brep with an unambiguous source layer. Never force equal counts by index.

`scripts/c4d/rebuild_layers_from_rhino.py` is a reusable equal-count Layer-mode implementation. Do not use it for Block mode or split-mesh leftovers; generate a task-specific guarded mutation through `c4d-remote-executor` for those cases.

Leave the rebuilt C4D document open for review. Save a `.c4d` only when the user requests a destination or confirms the result. Do not report the pipeline complete while required artifacts remain scattered in a temporary staging folder.
