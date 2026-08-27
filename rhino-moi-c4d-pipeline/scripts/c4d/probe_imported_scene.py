import json
import os

import c4d


# Inject an absolute writable path before sending through c4d-remote-executor.
OUTPUT_PATH = globals().get("OUTPUT_PATH", r"C:\path\to\c4d_scene_probe.json")


def vector_data(value):
    return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}


def matrix_data(value):
    return {
        "off": vector_data(value.off),
        "v1": vector_data(value.v1),
        "v2": vector_data(value.v2),
        "v3": vector_data(value.v3),
    }


def bounds(points):
    if not points:
        return None
    minimum = c4d.Vector(points[0])
    maximum = c4d.Vector(points[0])
    for point in points[1:]:
        minimum.x = min(minimum.x, point.x)
        minimum.y = min(minimum.y, point.y)
        minimum.z = min(minimum.z, point.z)
        maximum.x = max(maximum.x, point.x)
        maximum.y = max(maximum.y, point.y)
        maximum.z = max(maximum.z, point.z)
    return {
        "min": vector_data(minimum),
        "max": vector_data(maximum),
        "center": vector_data((minimum + maximum) * 0.5),
        "size": vector_data(maximum - minimum),
    }


def object_path(obj):
    parts = []
    current = obj
    while current is not None:
        parts.append(current.GetName())
        current = current.GetUp()
    parts.reverse()
    return "/" + "/".join(parts)


def walk(obj, depth, records):
    while obj is not None:
        record = {
            "name": obj.GetName(),
            "path": object_path(obj),
            "depth": int(depth),
            "type_id": int(obj.GetType()),
            "type_name": obj.GetTypeName(),
            "matrix_global": matrix_data(obj.GetMg()),
            "bbox_center_local": vector_data(obj.GetMp()),
            "bbox_radius_local": vector_data(obj.GetRad()),
            "children": 0,
        }
        child = obj.GetDown()
        cursor = child
        while cursor is not None:
            record["children"] += 1
            cursor = cursor.GetNext()

        if obj.CheckType(c4d.Opolygon):
            local_points = list(obj.GetAllPoints())
            global_matrix = obj.GetMg()
            world_points = [point * global_matrix for point in local_points]
            record["point_count"] = int(obj.GetPointCount())
            record["polygon_count"] = int(obj.GetPolygonCount())
            record["bbox_local_exact"] = bounds(local_points)
            record["bbox_world_exact"] = bounds(world_points)

        records.append(record)
        if child is not None:
            walk(child, depth + 1, records)
        obj = obj.GetNext()


def main():
    if OUTPUT_PATH == r"C:\path\to\c4d_scene_probe.json":
        raise RuntimeError("Set OUTPUT_PATH before running this script")
    doc = c4d.documents.GetActiveDocument()
    records = []
    walk(doc.GetFirstObject(), 0, records)

    polygon_records = [item for item in records if item["type_id"] == int(c4d.Opolygon)]
    polygons = []
    stack = list(doc.GetObjects())
    while stack:
        obj = stack.pop()
        child = obj.GetDown()
        while child is not None:
            stack.append(child)
            child = child.GetNext()
        if obj.CheckType(c4d.Opolygon):
            polygons.append(obj)
    normal_tag_count = sum(
        1 for obj in polygons for tag in obj.GetTags() if tag.CheckType(c4d.Tnormal)
    )
    material_tag_count = sum(
        1 for obj in polygons for tag in obj.GetTags() if tag.CheckType(c4d.Ttexture)
    )
    data = {
        "document_name": doc.GetDocumentName(),
        "document_path": doc.GetDocumentPath(),
        "object_count": len(records),
        "top_level_count": len(doc.GetObjects()),
        "polygon_object_count": len(polygon_records),
        "material_count": len(doc.GetMaterials()),
        "normal_tag_count": normal_tag_count,
        "material_tag_count": material_tag_count,
        "objects": records,
    }
    directory = os.path.dirname(OUTPUT_PATH)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)

    type_counts = {}
    for item in records:
        key = "{0}:{1}".format(item["type_id"], item["type_name"])
        type_counts[key] = type_counts.get(key, 0) + 1

    global _result
    _result = {
        "execution_ok": True,
        "verification_ok": True,
        "output_path": OUTPUT_PATH,
        "document_name": data["document_name"],
        "object_count": data["object_count"],
        "top_level_count": data["top_level_count"],
        "polygon_object_count": data["polygon_object_count"],
        "material_count": data["material_count"],
        "normal_tag_count": data["normal_tag_count"],
        "material_tag_count": data["material_tag_count"],
        "type_counts": type_counts,
        "top_level_names": [obj.GetName() for obj in doc.GetObjects()],
    }


main()
