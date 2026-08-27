import itertools
import json

import c4d


METADATA_PATH = globals().get("METADATA_PATH", r"C:\path\to\rhino_metadata.json")
ROOT_NAME = globals().get("ROOT_NAME", "RHINO_METADATA_REBUILT")
GEOMETRY_TYPES = ("Brep", "Extrusion", "Mesh", "Surface", "SubD")
MAX_MATCH_ERROR = float(globals().get("MAX_MATCH_ERROR", 0.1))
MAX_AMBIGUOUS_GAP = float(globals().get("MAX_AMBIGUOUS_GAP", 0.0001))


def exact_world_bbox(obj):
    points = list(obj.GetAllPoints())
    if not points:
        return None
    matrix = obj.GetMg()
    world_points = [point * matrix for point in points]
    minimum = c4d.Vector(world_points[0])
    maximum = c4d.Vector(world_points[0])
    for point in world_points[1:]:
        minimum.x = min(minimum.x, point.x)
        minimum.y = min(minimum.y, point.y)
        minimum.z = min(minimum.z, point.z)
        maximum.x = max(maximum.x, point.x)
        maximum.y = max(maximum.y, point.y)
        maximum.z = max(maximum.z, point.z)
    return {
        "min": [float(minimum.x), float(minimum.y), float(minimum.z)],
        "max": [float(maximum.x), float(maximum.y), float(maximum.z)],
    }


def rhino_bbox_mapped(item, permutation, signs):
    bbox = item.get("bbox")
    if not bbox:
        return None
    source_minimum = [bbox["min"]["x"], bbox["min"]["y"], bbox["min"]["z"]]
    source_maximum = [bbox["max"]["x"], bbox["max"]["y"], bbox["max"]["z"]]
    minimum = []
    maximum = []
    for target_axis, source_axis in enumerate(permutation):
        sign = signs[target_axis]
        first = sign * source_minimum[source_axis]
        second = sign * source_maximum[source_axis]
        minimum.append(min(first, second))
        maximum.append(max(first, second))
    return {"min": minimum, "max": maximum}


def bbox_error(left, right):
    return max(
        abs(float(left[side][axis]) - float(right[side][axis]))
        for side in ("min", "max")
        for axis in range(3)
    )


def union_bbox(items):
    if not items or any(item is None for item in items):
        raise RuntimeError("Every matched geometry must have a valid bounding box")
    return {
        "min": [min(item["min"][axis] for item in items) for axis in range(3)],
        "max": [max(item["max"][axis] for item in items) for axis in range(3)],
    }


def bbox_center(value):
    return [(value["min"][axis] + value["max"][axis]) * 0.5 for axis in range(3)]


def bbox_size(value):
    return [value["max"][axis] - value["min"][axis] for axis in range(3)]


def translate_bbox(value, translation):
    return {
        side: [value[side][axis] + translation[axis] for axis in range(3)]
        for side in ("min", "max")
    }


def mapping_name(permutation, signs):
    names = ("X", "Y", "Z")
    return ", ".join(
        "C4D {0}={1}Rhino {2}".format(
            names[index], "+" if signs[index] > 0 else "-", names[source_axis]
        )
        for index, source_axis in enumerate(permutation)
    )


def hungarian_assignment(costs):
    count = len(costs)
    if any(len(row) != count for row in costs):
        raise RuntimeError("Geometry matching requires equal Rhino and C4D counts")

    u = [0.0] * (count + 1)
    v = [0.0] * (count + 1)
    p = [0] * (count + 1)
    way = [0] * (count + 1)
    for row in range(1, count + 1):
        p[0] = row
        column0 = 0
        minimum = [float("inf")] * (count + 1)
        used = [False] * (count + 1)
        while True:
            used[column0] = True
            row0 = p[column0]
            delta = float("inf")
            column1 = 0
            for column in range(1, count + 1):
                if used[column]:
                    continue
                current = costs[row0 - 1][column - 1] - u[row0] - v[column]
                if current < minimum[column]:
                    minimum[column] = current
                    way[column] = column0
                if minimum[column] < delta:
                    delta = minimum[column]
                    column1 = column
            for column in range(count + 1):
                if used[column]:
                    u[p[column]] += delta
                    v[column] -= delta
                else:
                    minimum[column] -= delta
            column0 = column1
            if p[column0] == 0:
                break
        while True:
            column1 = way[column0]
            p[column0] = p[column1]
            column0 = column1
            if column0 == 0:
                break

    assignment = [-1] * count
    for column in range(1, count + 1):
        assignment[p[column] - 1] = column - 1
    return assignment


def normalized_name(value):
    return (value or "").strip().casefold()


def polygon_material_names(polygon):
    names = []
    for tag in polygon.GetTags():
        if not tag.CheckType(c4d.Ttexture):
            continue
        material = tag.GetMaterial()
        if material is not None:
            names.append(normalized_name(material.GetName()))
    return names


def match_geometry(rhino_geometry, polygons):
    polygon_bboxes = [exact_world_bbox(obj) for obj in polygons]
    c4d_overall = union_bbox(polygon_bboxes)
    candidates = []
    for permutation in itertools.permutations((0, 1, 2)):
        for signs in itertools.product((-1, 1), repeat=3):
            mapped = [rhino_bbox_mapped(item, permutation, signs) for item in rhino_geometry]
            rhino_overall = union_bbox(mapped)
            translation = [
                right - left
                for left, right in zip(bbox_center(rhino_overall), bbox_center(c4d_overall))
            ]
            translated = [translate_bbox(item, translation) for item in mapped]
            size_error = max(
                abs(left - right)
                for left, right in zip(bbox_size(rhino_overall), bbox_size(c4d_overall))
            )
            candidates.append({
                "permutation": permutation,
                "signs": signs,
                "mapping": mapping_name(permutation, signs),
                "translation": translation,
                "size_error": size_error,
                "bboxes": translated,
            })

    minimum_size_error = min(item["size_error"] for item in candidates)
    candidates = [
        item for item in candidates if item["size_error"] <= minimum_size_error + 0.001
    ]
    for candidate in candidates:
        nearest = [
            min(bbox_error(rhino_bbox, polygon_bbox) for polygon_bbox in polygon_bboxes)
            for rhino_bbox in candidate["bboxes"]
        ]
        candidate["nearest_sum"] = sum(nearest)
        candidate["nearest_max"] = max(nearest)
    candidates.sort(key=lambda item: (item["nearest_sum"], item["nearest_max"]))
    best = candidates[0]

    raw_costs = [
        [bbox_error(rhino_bbox, polygon_bbox) for polygon_bbox in polygon_bboxes]
        for rhino_bbox in best["bboxes"]
    ]
    costs = [list(row) for row in raw_costs]
    material_names = [polygon_material_names(polygon) for polygon in polygons]
    material_tiebreak_resolved = 0
    for row_index, row in enumerate(raw_costs):
        minimum = min(row)
        candidates = [
            column
            for column, value in enumerate(row)
            if value <= minimum + MAX_AMBIGUOUS_GAP
        ]
        if len(candidates) < 2:
            continue
        layer_leaf = normalized_name(
            (rhino_geometry[row_index].get("layer") or "").split("::")[-1]
        )
        exact_material_matches = [
            column for column in candidates if layer_leaf in material_names[column]
        ]
        if layer_leaf and len(exact_material_matches) == 1:
            preferred = exact_material_matches[0]
            for column in candidates:
                if column != preferred:
                    costs[row_index][column] += MAX_AMBIGUOUS_GAP * 2.0
            material_tiebreak_resolved += 1

    assignment = hungarian_assignment(costs)
    assigned_errors = [raw_costs[row][column] for row, column in enumerate(assignment)]
    ambiguous = 0
    for row in costs:
        ordered = sorted(row)
        if len(ordered) > 1 and ordered[1] - ordered[0] <= MAX_AMBIGUOUS_GAP:
            ambiguous += 1

    if max(assigned_errors) > MAX_MATCH_ERROR:
        raise RuntimeError(
            "BBox matching is not reliable: max error {0:.6f} exceeds {1:.6f}".format(
                max(assigned_errors), MAX_MATCH_ERROR
            )
        )
    if ambiguous:
        raise RuntimeError(
            "BBox matching is ambiguous for {0} Rhino objects; refusing to rebuild".format(
                ambiguous
            )
        )

    return assignment, {
        "mapping": best["mapping"],
        "translation": best["translation"],
        "overall_size_error": best["size_error"],
        "max_error": max(assigned_errors),
        "median_error": sorted(assigned_errors)[len(assigned_errors) // 2],
        "ambiguous": ambiguous,
        "material_tiebreak_resolved": material_tiebreak_resolved,
        "identity_assignments": sum(
            1 for row, column in enumerate(assignment) if row == column
        ),
    }


def validate_scene(doc, metadata):
    if doc.SearchObject(ROOT_NAME) is not None:
        raise RuntimeError(
            "Scene already contains {0}; undo or remove it before running again".format(
                ROOT_NAME
            )
        )
    if metadata.get("counts", {}).get("instance_definitions", 0):
        raise RuntimeError(
            "This script rebuilds flat Layer hierarchy only; use the Block hierarchy script instead"
        )

    top_level = list(doc.GetObjects())
    if any(not obj.CheckType(c4d.Opolygon) for obj in top_level):
        raise RuntimeError("Expected a flat polygon-only C4D import")
    rhino_geometry = [
        item for item in metadata.get("objects", []) if item.get("type") in GEOMETRY_TYPES
    ]
    if len(rhino_geometry) != len(top_level):
        raise RuntimeError(
            "Geometry count mismatch: Rhino has {0}, C4D has {1}".format(
                len(rhino_geometry), len(top_level)
            )
        )
    return rhino_geometry, top_level


def layer_parent(doc, root, layer_nodes, path):
    if not path:
        path = "Unlayered"
    parts = path.split("::")
    parent = root
    current_parts = []
    for part in parts:
        current_parts.append(part)
        current_path = "::".join(current_parts)
        if current_path not in layer_nodes:
            node = c4d.BaseObject(c4d.Onull)
            node.SetName(part or "Unnamed_Layer")
            node.InsertUnderLast(parent)
            doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, node)
            layer_nodes[current_path] = node
        parent = layer_nodes[current_path]
    return parent


def geometry_name(item, index, count):
    if item.get("name"):
        return item["name"]
    layer_name = (item.get("layer") or "Unlayered").split("::")[-1]
    if count == 1:
        return layer_name
    return "{0}__Geo_{1:03d}".format(layer_name, index + 1)


def main():
    if METADATA_PATH == r"C:\path\to\rhino_metadata.json":
        raise RuntimeError("Set METADATA_PATH before running this script")
    with open(METADATA_PATH, "r", encoding="utf-8") as stream:
        metadata = json.load(stream)

    doc = c4d.documents.GetActiveDocument()
    rhino_geometry, polygons = validate_scene(doc, metadata)
    assignment, match = match_geometry(rhino_geometry, polygons)

    layer_counts = {}
    for item in rhino_geometry:
        path = item.get("layer") or "Unlayered"
        layer_counts[path] = layer_counts.get(path, 0) + 1
    layer_indices = {}
    layer_nodes = {}

    doc.StartUndo()
    try:
        c4d.StopAllThreads()
        root = c4d.BaseObject(c4d.Onull)
        root.SetName(ROOT_NAME)
        doc.InsertObject(root)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, root)

        for rhino_index, item in enumerate(rhino_geometry):
            polygon = polygons[assignment[rhino_index]]
            parent = layer_parent(doc, root, layer_nodes, item.get("layer"))
            path = item.get("layer") or "Unlayered"
            layer_index = layer_indices.get(path, 0)
            layer_indices[path] = layer_index + 1
            global_matrix = polygon.GetMg()
            doc.AddUndo(c4d.UNDOTYPE_HIERARCHY_PSR, polygon)
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, polygon)
            polygon.InsertUnderLast(parent)
            polygon.SetMg(global_matrix)
            polygon.SetName(geometry_name(item, layer_index, layer_counts[path]))
    finally:
        doc.EndUndo()

    c4d.EventAdd()
    remaining_generic = sum(
        1 for polygon in polygons if polygon.GetName().lower().startswith("obj")
    )
    global _result
    _result = {
        "execution_ok": True,
        "verification_ok": (
            len(doc.GetObjects()) == 1
            and doc.GetObjects()[0].GetName() == ROOT_NAME
            and remaining_generic == 0
        ),
        "request_id": metadata.get("automation", {}).get("request_id"),
        "container": ROOT_NAME,
        "reparented_polygons": len(polygons),
        "created_layer_nulls": len(layer_nodes),
        "remaining_generic_names": remaining_generic,
        "top_level_objects": len(doc.GetObjects()),
        "match": match,
    }


main()
