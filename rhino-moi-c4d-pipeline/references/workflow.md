# End-to-end workflow

## 1. Preflight and metadata

1. Load and follow the external `c4d-remote-executor` Skill before operating C4D. Use the bundled Rhino exporter described in `references/rhino-metadata-export.md`; there is no separate Rhino metadata Skill dependency.
2. Confirm one `Rhino.exe` process, inspect the active document path and modified state, and record the open C4D documents.
3. Run `scripts/rhino-metadata/invoke_export.ps1` from this Skill and retain the matching `automation.request_id` for every later artifact.
4. Count top-level InstanceReference, Brep, Curve, Point, Layer, and Definition records.
5. Decide whether the visible model still contains live Block instances. A single-looking viewport object is not sufficient evidence.
6. If Block explosion is required, capture metadata first and perform it only on a controlled working copy. If top-level instance references are zero, skip `ExplodeBlock`.

## 2. Rhino 5 copy

Prefer a script over the Save As dialog:

- Read the source with `Rhino.FileIO.File3dm.Read(source)`.
- Write a new file with `model.Write(output, 5)`.
- Refuse overwrite, confirm the active document path still matches the source, and confirm the active document remains unmodified.
- Serialize Rhino IronPython response JSON with `ensure_ascii=True` so Unicode paths cannot fail on an ASCII response stream.
- Put process files in an ASCII-only folder such as `codex_export_fbx`; keep the source file untouched.

Treat the Rhino 5 file and the automation response as separate commit points. If the file is nonzero but the response is missing or malformed, do not overwrite or blindly rerun the write. Verify the existing file, source path, active path, and modified state; then recover by publishing an ASCII-safe response that marks the output as preexisting.

If MoI cannot open a path containing Chinese characters, make an additional byte-identical staging copy under an ASCII-only absolute path. This is a compatibility copy, not a replacement for the source-side Rhino 5 artifact.

## 3. MoI FBX export

Open the Rhino 5 copy in MoI. When no stable MoI scripting interface is available, use computer control and visually verify every value before confirming.

Required Meshing options:

- polygon slider: same high-detail position as the approved reference;
- `Output`: `N-gons`;
- `Display`: `Shaded + edges`;
- `Weld vertices along edges`: checked;
- `Angle`: `3`;
- `Divide larger than`: `20`, mode `All`;
- `Avoid smaller than`: `.5`;
- `Aspect ratio limit`: `0`.

Verify the FBX exists, is nonzero, and has an ASCII-compatible filename.
When MoI exposes preview polygon/point counts, record them with the chosen settings as diagnostic evidence; they are not a substitute for the C4D import probe.

## 4. C4D import and Normal tags

1. Preserve every previously open C4D document. Load the FBX as a separate document.
2. For scripted loading in C4D 2024, use `SCENEFILTER_OBJECTS | SCENEFILTER_MATERIALS`; `SCENEFILTER_NONE` can return an empty document.
3. Before exposing the document for mutation, probe it and require:
   - polygon-only flat import;
   - a material count consistent with the source/export expectations, including zero when the source genuinely has no materials;
   - one Normal tag on every Polygon;
   - C4D importer behavior equivalent to `Normals: Normal Tags`.
   Use the bundled `scripts/c4d/probe_imported_scene.py` through `c4d-remote-executor` when it fits the current C4D version, injecting an absolute `OUTPUT_PATH`.
4. Before insertion, copy previous-document names and paths into ordinary Python values. After `InsertBaseDocument()`, re-enumerate live documents; do not dereference a stale `BaseDocument` wrapper, which C4D may invalidate.
5. Insert and activate the validated document without closing or overwriting the previous document.

If an exception, empty socket response, or timeout occurs after document insertion or another side effect, classify completion as unknown. Use `c4d-remote-executor` read-only probes and its lifecycle evidence to inspect the active documents before deciding whether any retry is safe.

## 5. Geometry matching

Build exact world BBoxes from C4D polygon points, not only object radii. Generate plausible axis permutations, signs, scale, and translation candidates, then re-derive or directly validate the transform for every scene. A mapping seen in a previous case is only a candidate, never a default.

Do not select a transform only from the overall scene bounds: Rhino curves, points, construction geometry, or objects that MoI omits can skew the overall bounds and make a wrong mapping appear numerically better. Require support from multiple object-level correspondences.

For equal counts:

1. Generate all plausible axis permutations/signs.
2. Build the Rhino-to-C4D BBox cost matrix.
3. Use Hungarian assignment.
4. Use material/layer leaf names only inside the geometry ambiguity gap, never as primary identity. Permit the tie-break only when one candidate's C4D material name exactly matches the Rhino Layer leaf and that exact match is unique; otherwise keep the row ambiguous.
5. Record how many assignments the material tie-break resolved and independently verify that each resolved Polygon is under the expected Layer Null with the expected material.
6. Reject excessive maximum error or unresolved equal-cost candidates.

For `C4D Polygon count > Rhino Brep count`:

1. Globally assign every Rhino Brep to a unique C4D Polygon.
2. Require all Brep assignments to remain under the accepted geometry tolerance.
3. Inspect the unassigned C4D meshes. Face-material splits commonly retain the same source envelope while producing different material tags.
4. Attach a leftover only when its BBox is contained by, or is within an explicitly justified meshing tolerance of, a matched Brep and resolves to one Rhino layer path.
5. Record the split count and containment tolerance in the case log.

Curves and points must not be silently treated as Breps. If MoI does not emit corresponding polygons, omit them from geometry matching and preserve the fact in the report.

## 6. Hierarchy mutation

Choose Block or Layer reconstruction from the metadata, not from C4D names.

For an equal-count Layer scene, `scripts/c4d/rebuild_layers_from_rhino.py` is the maintained starting implementation. Inject `METADATA_PATH` and evidence-backed thresholds before sending it through `c4d-remote-executor`. It intentionally rejects Block mode and count differences.

Before mutation validate the active document name, polygon count, topology, Normal tags, material tags, names, BBoxes, and metadata request ID. Then:

1. save each Polygon `GetMg()`;
2. create `RHINO_METADATA_REBUILT` and the required Null tree;
3. register Undo for new Nulls, hierarchy changes, and renames;
4. `InsertUnderLast()` the Polygon;
5. restore `SetMg()`;
6. rename from Rhino Definition or Layer context;
7. call `c4d.EventAdd()`.

## 7. Acceptance gate

Run an independent read-only probe and report:

- top-level root and direct children;
- total objects, Nulls, and Polygons;
- Normal-tag and material-tag counts;
- remaining `obj*` names;
- hierarchy depth;
- per-object and overall world-BBox errors;
- the unordered per-Polygon topology/geometry signature `(point_count, polygon_count, exact_world_bbox)` before and after hierarchy mutation;
- every material-resolved tie-break path and its final material;
- C4D protection backup path/hash when available;
- whether the final document was saved or intentionally left open and unsaved.

The prior C4D documents and the active Rhino source must still exist and remain unchanged.

Render a framed preview when geometry visibility matters. If C4D successfully writes a nonzero preview but the client-side inspector lacks an image dependency, inspect that file with another available image viewer instead of rerunning the scene mutation. Re-probe afterward to confirm any temporary preview camera was removed.

## 8. Artifact consolidation

ASCII staging is a transport workaround, not the final delivery location.

1. Resolve and verify the exact staging and source-side destination paths.
2. Use `<original model folder>\codex_export_fbx` as the default final artifact directory unless the user specifies another location.
3. Move the FBX and any other unique process artifacts into that directory.
4. If the destination already contains a same-named Rhino 5 or FBX file, compare SHA-256 before cleanup. Delete the staging duplicate only when hashes match; never overwrite a different file.
5. Re-list the destination and record file sizes and hashes.
6. Remove the staging directory only after proving it is empty. Avoid recursive deletion for this cleanup.
7. Report the final paths. If the open C4D document was loaded from the former staging path, clarify that future reimports must use the consolidated FBX path.

## Stop and request help

Stop instead of accumulating errors when:

- Rhino process count is not exactly one;
- Rhino modified state or active path changes unexpectedly;
- MoI dialogs differ from the approved settings and cannot be interpreted confidently;
- a file dialog corrupts a Unicode path and ASCII staging does not resolve it;
- C4D imports no objects or omits Normal tags;
- geometry counts differ and the leftovers cannot be explained as verified splits or omitted non-mesh objects;
- matching is ambiguous or exceeds the chosen tolerance;
- a script fails after any C4D side effect and a read-only probe cannot establish the resulting state;
- C4D protection fails or a bridge timeout leaves completion unknown;
- final artifacts cannot be consolidated without overwriting a different destination file.
