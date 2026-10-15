# Preparing a Rhino working copy

Read this before exporting the Rhino 5 conversion copy, especially for an unsaved document or nested Blocks. These steps preserve the loaded source while preparing geometry that MoI can read.

## Export the metadata's source state

Capture `(int(doc.RuntimeSerialNumber), doc.Path, bool(doc.Modified))` before export. A missing path is valid for an unsaved or imported document. Preserve this tuple after each operation; do not save the source or reset its modified flag to make a check pass.

- When the saved source represents the current metadata snapshot, read it with `Rhino.FileIO.File3dm.Read(source)` and write the copy with `model.Write(output, 5)`.
- When no saved path exists or the loaded document has changes, copy the loaded document. Reading an older file would silently separate the geometry from its metadata.

For Rhino 7, the following API was verified for writing an unsaved document without changing its path or modified state. Resolve a distinct writable `output` path and refuse an existing file before calling it:

```python
before = (int(doc.RuntimeSerialNumber), doc.Path, bool(doc.Modified))
options = Rhino.FileIO.FileWriteOptions()
options.UpdateDocumentPath = False
options.FileVersion = 5
options.SuppressDialogBoxes = True
options.SuppressAllInput = True
written = doc.Write3dmFile(output, options)
after = (int(doc.RuntimeSerialNumber), doc.Path, bool(doc.Modified))
if not written or before != after:
    raise RuntimeError("Copy export failed or the source document state changed")
```

Validate the output independently: require a nonzero file, reopen it as a `File3dm`, and compare expected geometry and Block counts with the metadata. Keeping the tuple unchanged is necessary but does not alone prove the copy contains the expected model. Before using this API on an initially modified source, verify modified-state preservation in a disposable document; the unsaved, unmodified case does not establish that behavior.

Serialize response JSON with `ensure_ascii=True`. Treat file publication and response publication as separate commit points, as described in [workflow.md](workflow.md).

## Expand Block occurrences outside the source document

Use the original metadata to walk each top-level occurrence recursively. Carry an occurrence key, parent key, Block path, and accumulated transform; multiply the outer transform by the nested instance transform. Detect cycles on the current recursion path, so repeated uses of the same definition remain valid.

For each geometry occurrence:

1. Duplicate the source geometry and attributes in memory. Apply the accumulated transform to the duplicated geometry and check that it succeeds.
2. Remap the source layer index into the destination `File3dm`. Preserve source layer paths and material provenance in metadata. If the copy cannot preserve an attribute the task needs, stop instead of silently dropping it.
3. Normalize the copied attributes for a standalone object. Block definition members can retain `ObjectMode.InstanceDefinitionObject` even when `Visible` is true and their Breps are valid; MoI can then show an empty model. Set `attributes.Mode = Rhino.DocObjects.ObjectMode.Normal` on the copy, and handle source visibility and locking deliberately.
4. Add geometry through its supported typed API. For a Brep in Rhino 7, use `working.Objects.AddBrep(geometry, attributes)`; `File3dmObjectTable.Add` does not accept that argument pair. Probe other geometry types before using their APIs, or stop if they are outside the supported export path.
5. Measure the world BBox from the transformed geometry and retain it with the occurrence metadata. An axis-aligned definition BBox transformed by its corners can overestimate rotated geometry.

In the verified Rhino 7 API, `Layer` has no `Duplicate()` method and `File3dmLayerTable.Add` did not return an index. Create destination layers explicitly with the required attributes and maintain a verified source-to-destination index map; do not cast a mutation method's return value to an index without checking its contract.

Write a distinct Rhino 5 file. Reopen it and require the expected occurrence count, valid supported geometry, valid destination layer indices, and standalone object modes before using MoI. Compare the source identity and modified state again. Keep the original Block metadata for C4D reconstruction; the flattened transport copy is not the source of assembly identity.
