# Bundled Rhino metadata export

Use this component to export object, Layer, Block, transform, bounding-box, color, and material metadata from the active document in one running Rhino 7 instance. It is read-only with respect to the active Rhino document and requires no Rhino plug-in or manual ScriptEditor step.

## Run the exporter

1. Require Windows, Rhino 7, and exactly one running `Rhino.exe` process.
   - If none are running, stop and ask the user to open Rhino and the intended document.
   - If more than one is running, stop without connecting and ask the user to leave only the intended instance open.
   - Never close Rhino instances automatically.
2. Choose an absolute writable output path outside the Skill folder. Keep runtime metadata out of version control unless the user explicitly requests a fixture.
3. Resolve the directory containing this Skill's `SKILL.md`, then run its wrapper by absolute path:

```powershell
& '<skill-root>\scripts\rhino-metadata\invoke_export.ps1' -OutputPath 'C:\absolute\path\rhino_metadata.json'
```

4. Treat a nonzero exit code or a JSON response with `ok: false` as failure.
5. Before consuming metadata, verify the returned `request_id`, `output_path`, document path, and object counts. Require the metadata `automation.request_id` to match the current response.

The wrapper writes request and response files under `%LOCALAPPDATA%\Codex\RhinoMetadataExport`, invokes `export_rhino_metadata.py` through `Rhino.Interface.7`, and waits for a matching response. The exporter atomically publishes the metadata before its response, preventing stale or partial JSON from being accepted.

## Output contract

The exporter keeps schema version 2 for the reconstruction scripts. It includes:

- document identity, units, tolerance, coordinate-system conventions, and automation request data;
- Layer table and full Layer paths;
- top-level objects and Block/Instance definitions;
- definition members, nested instances, transforms, and bounding boxes;
- object names, types, colors, materials, groups, visibility, locking, and user strings.

## Guardrails and recovery

- Do not modify, save, close, or change selection in the Rhino document.
- Do not reuse an output solely because it exists; accept only the current matching request ID.
- Do not bypass the single-instance check.
- Treat COM failure or timeout as unknown completion. Inspect the response and output request ID before retrying.
- If a nonzero metadata file exists but the response is missing or malformed, verify its request ID and the unchanged active document before deciding whether recovery is safe.

## Supplemental IronPython probes

When the bundled metadata is insufficient and a read-only Rhino 7 probe is needed:

- Convert CLR scalar values to the intended Python JSON types explicitly. For example, use `int(doc.RuntimeSerialNumber)`; a CLR number can print like an integer while IronPython's JSON encoder rejects it as `is not JSON serializable`. Preserve numeric fields as numbers rather than using a blanket string fallback. The bundled exporter already converts this field.
- For a small probe response, call `json.dumps` before opening the destination for writing. A serialization failure must not truncate an existing response or leave partial JSON that looks like a result. Keep the bundled exporter's temporary-file publication strategy for full metadata.
- Catch probe exceptions and return an `ok: false` response with the current request ID and traceback. When that failure response has been written successfully, do not re-raise into Rhino's interactive error dialog: it can hold a synchronous COM call until someone dismisses it. The caller must check the response, not just whether `RunScript` returned. If no valid response can be written, treat completion as unknown and inspect before retrying.

These rules apply to supplemental probes; reuse the bundled exporter for the normal metadata snapshot.
