"""Read-only, bounded industrial asset audit. Run inside Blender's Python.

No scene mutation, repair, save, selection change, or renderer change is performed.
Reports are evidence for review, never a complete asset-acceptance certificate.
"""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


SAMPLE_LIMIT = 24


def _finite(values):
    return all(math.isfinite(float(value)) for value in values)


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _subtree(root):
    result, seen, queue = [], set(), [(root, 0)]
    while queue:
        obj, depth = queue.pop()
        if obj.as_pointer() in seen:
            raise ValueError("Cycle or repeated object in requested hierarchy")
        seen.add(obj.as_pointer())
        result.append((obj, depth))
        queue.extend((child, depth + 1) for child in reversed(sorted(obj.children, key=lambda o: o.name)))
    return result


def _bounds(points):
    if not points:
        return None
    lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    return {"min": list(lo), "max": list(hi), "size": list(hi - lo)}


def _signature(points, tolerance):
    return tuple(sorted(tuple(round(float(c) / tolerance) for c in p) for p in points))


def _mesh_metrics(mesh, matrix, tolerance, proximity_limit):
    local = [v.co.copy() for v in mesh.vertices]
    world = [matrix @ co for co in local]
    result = {
        "vertices": len(local), "edges": len(mesh.edges), "faces": len(mesh.polygons),
        "triangles": 0, "uv_layers": len(mesh.uv_layers),
        "nonfinite_vertices": sum(not _finite(co) for co in world),
    }
    if result["nonfinite_vertices"]:
        return result, world
    result["bounds_world"] = _bounds(world)
    edge_faces, used_vertices = defaultdict(list), set()
    small_faces = []
    for poly in mesh.polygons:
        indices = list(poly.vertices)
        used_vertices.update(indices)
        if indices:
            origin = world[indices[0]]
            area = sum(((world[indices[i]] - origin).cross(world[indices[i + 1]] - origin)).length * .5
                       for i in range(1, len(indices) - 1))
            if area <= tolerance * tolerance:
                small_faces.append(poly.index)
        for a, b in zip(indices, indices[1:] + indices[:1]):
            edge_faces[tuple(sorted((a, b)))].append((poly.index, a, b))

    wire_edges, zero_edges, edge_vertices = 0, 0, set()
    for edge in mesh.edges:
        a, b = edge.vertices
        edge_vertices.update((a, b))
        wire_edges += not edge_faces.get(tuple(sorted((a, b))))
        zero_edges += (world[a] - world[b]).length <= tolerance
    result.update({
        "zero_area_faces": len(small_faces), "zero_area_face_sample": small_faces[:SAMPLE_LIMIT],
        "zero_length_edges": zero_edges, "loose_edges": wire_edges,
        "loose_vertices": len(set(range(len(local))) - used_vertices - edge_vertices),
        "boundary_edges": sum(len(links) == 1 for links in edge_faces.values()),
        "nonmanifold_edges": sum(len(links) > 2 for links in edge_faces.values()),
        "inconsistent_winding_edges": sum(len(links) == 2 and links[0][1:] == links[1][1:]
                                          for links in edge_faces.values()),
    })

    if not world:
        result["near_vertex_candidates"] = {"status": "checked", "count": 0, "sample": []}
    elif len(world) <= proximity_limit:
        tree = KDTree(len(world))
        for i, point in enumerate(world):
            tree.insert(point, i)
        tree.balance()
        pairs, sample, comparisons, aborted = 0, [], 0, False
        # Bound dense coincident point clouds as well as vertex count.
        for i, point in enumerate(world):
            neighbors = tree.find_range(point, tolerance)
            comparisons += len(neighbors)
            if comparisons > 2_000_000:
                aborted = True
                break
            for _, j, distance in neighbors:
                if j > i:
                    pairs += 1
                    if len(sample) < SAMPLE_LIMIT:
                        sample.append([i, j, float(distance)])
        result["near_vertex_candidates"] = {
            "status": "partial" if aborted else "checked", "count": pairs,
            "sample": sample, "note": "Candidates can be intentional seams or separate shells.",
        }
    else:
        result["near_vertex_candidates"] = {"status": "skipped", "reason": "vertex budget exceeded"}

    # Connected face shells and local-space winding; a mirrored world transform is
    # reported separately so it is not misidentified as an inverted source shell.
    adjacency = [[] for _ in mesh.polygons]
    unclosed, inconsistent = set(), set()
    for links in edge_faces.values():
        face_ids = [item[0] for item in links]
        if len(links) != 2:
            unclosed.update(face_ids)
        if len(links) == 2 and links[0][1:] == links[1][1:]:
            inconsistent.update(face_ids)
        if len(face_ids) > 1:
            anchor = face_ids[0]
            for other in face_ids[1:]:
                adjacency[anchor].append(other)
                adjacency[other].append(anchor)
    mesh.calc_loop_triangles()
    result["triangles"] = len(mesh.loop_triangles)
    triangles_by_face = defaultdict(list)
    for tri in mesh.loop_triangles:
        triangles_by_face[tri.polygon_index].append(tuple(tri.vertices))
    unseen = set(range(len(mesh.polygons)))
    shells, inward, ambiguous, shell_sample = 0, 0, 0, []
    closed_shells = 0
    while unseen:
        first = unseen.pop()
        members, queue = {first}, [first]
        while queue:
            face_index = queue.pop()
            for nxt in adjacency[face_index]:
                if nxt in unseen:
                    unseen.remove(nxt)
                    members.add(nxt)
                    queue.append(nxt)
        shells += 1
        if members & (unclosed | inconsistent):
            continue
        closed_shells += 1
        ids = {v for f in members for v in mesh.polygons[f].vertices}
        origin = local[next(iter(ids))]
        box = _bounds([local[i] for i in ids])
        diagonal = Vector(box["size"]).length
        epsilon = max(diagonal ** 3 * 1e-12, 1e-30)
        volume = 0.
        for face_index in members:
            for a, b, c in triangles_by_face[face_index]:
                volume += (local[a] - origin).dot((local[b] - origin).cross(local[c] - origin)) / 6.
        if volume < -epsilon:
            inward += 1
            if len(shell_sample) < SAMPLE_LIMIT:
                shell_sample.append({"face": min(members), "signed_volume_local": volume})
        elif abs(volume) <= epsilon:
            ambiguous += 1
    result.update({"face_shells": shells, "closed_shells": closed_shells,
                   "inward_shell_candidates": inward, "ambiguous_closed_shells": ambiguous,
                   "inward_shell_sample": shell_sample})
    return result, world


def _image_checks(materials):
    images, visited = {}, set()

    def walk(tree):
        if not tree or tree.as_pointer() in visited:
            return
        visited.add(tree.as_pointer())
        for node in tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images[node.image.as_pointer()] = node.image
            elif node.type == "GROUP":
                walk(node.node_tree)

    for mat in materials.values():
        if mat.use_nodes:
            walk(mat.node_tree)
    findings = []
    for image in images.values():
        if image.source in {"GENERATED", "VIEWER"} or image.packed_file or image.packed_files:
            continue
        if image.source in {"TILED", "SEQUENCE", "MOVIE"}:
            findings.append({"code": "image_sequence_review", "image": image.name,
                             "reason": "Tile/frame completeness needs a dedicated check."})
            continue
        raw = image.filepath
        absolute = bpy.path.abspath(raw, library=image.library) if raw else ""
        if not absolute or not Path(absolute).is_file():
            findings.append({"code": "missing_image", "image": image.name, "path": absolute})
    return {"images_checked": len(images), "findings": findings}


def audit_asset(root_name, *, evaluated=True, tolerance=None, max_direct_children=24,
                max_vertices=250_000, max_faces=200_000):
    """Inspect a root subtree without editing Blender data or current UI state.

    tolerance is in world Blender units, not an engineering manufacturing tolerance.
    Limits intentionally produce skipped/partial coverage, never a false zero.
    """
    root = bpy.data.objects.get(root_name)
    if root is None or root.name not in bpy.context.scene.objects:
        raise ValueError(f"Root is missing from the current scene: {root_name}")
    if min(max_direct_children, max_vertices, max_faces) < 1:
        raise ValueError("Review and workload limits must be positive")
    entries = _subtree(root)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    box_points = []
    for obj, _ in entries:
        if obj.type == "MESH":
            value = obj.evaluated_get(depsgraph) if evaluated else obj
            for corner in value.bound_box:
                point = value.matrix_world @ Vector(corner)
                if _finite(point):
                    box_points.append(point)
    bounds = _bounds(box_points)
    diagonal = Vector(bounds["size"]).length if bounds else 1.
    tolerance = max(diagonal * 1e-7, 1e-9) if tolerance is None else float(tolerance)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("tolerance must be a finite positive number")
    report = {
        "schema_version": 1, "blender_version": bpy.app.version_string,
        "root": root.name, "source_file": bpy.data.filepath, "evaluated_meshes": evaluated,
        "unit_system": bpy.context.scene.unit_settings.system,
        "meters_per_blender_unit": bpy.context.scene.unit_settings.scale_length,
        "numerical_tolerance_blender_units": tolerance,
        "bounds_world": bounds, "objects": [], "issues": [],
        "coverage": {
            "hierarchy": "checked", "mesh_topology": "checked", "exact_face_signatures": "checked",
            "near_vertex_candidates": "checked", "external_images": "checked",
            "not_checked": ["partial_or_differently_tessellated_coplanar_overlaps", "near_coplanar_z_fighting",
                            "self_intersections", "continuous_collisions", "uv_quality", "visual_shading",
                            "reference_fidelity", "mechanical_validity", "target_engine"],
        },
        "asset_acceptance": "not_determined",
    }

    def issue(code, obj, severity, count=1, detail=None):
        entry = {"code": code, "object": obj, "severity": severity, "count": int(count)}
        if detail is not None:
            entry["detail"] = detail
        report["issues"].append(entry)

    face_index, indexed_faces, cross_count, cross_sample = {}, 0, 0, []
    materials = {}
    for obj, depth in entries:
        matrix = obj.matrix_world
        record = {"name": obj.name, "type": obj.type, "depth": depth,
                  "parent": obj.parent.name if obj.parent else None,
                  "direct_children": len(obj.children), "local_scale": list(obj.scale),
                  "world_location": list(matrix.translation),
                  "role": str(obj.get("industrial_role", "unspecified")),
                  "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
        report["objects"].append(record)
        if len(obj.children) > max_direct_children:
            issue("hierarchy_fanout_review", obj.name, "review", len(obj.children),
                  "Group by function and merge rigid detail; the threshold is only a review heuristic.")
        if re.fullmatch(r"(?:Cube|Plane|Cylinder|Sphere|Empty)(?:\.\d+)?", obj.name):
            issue("generic_name", obj.name, "review")
        if not _finite(c for row in matrix for c in row):
            issue("nonfinite_transform", obj.name, "error")
            for key in ("mesh_topology", "exact_face_signatures", "near_vertex_candidates"):
                report["coverage"][key] = "partial"
            record["geometry_check"] = {"status": "skipped", "reason": "nonfinite transform"}
            continue
        if matrix.determinant() < 0:
            issue("negative_world_determinant", obj.name, "review")
        if any(abs(float(s) - 1.) > 1e-6 for s in obj.scale):
            issue("nonunit_local_scale", obj.name, "review", detail="Do not blindly apply motion/rig transforms.")
        for slot in obj.material_slots:
            if slot.material:
                materials[slot.material.as_pointer()] = slot.material
        if obj.type != "MESH":
            if obj.type in {"CURVE", "SURFACE", "FONT", "META", "VOLUME", "POINTCLOUD"} or obj.instance_type != "NONE":
                issue("uninspected_geometry", obj.name, "review", detail="Inspect or realize a scoped export copy.")
                report["coverage"]["mesh_topology"] = "partial"
            continue

        value = obj.evaluated_get(depsgraph) if evaluated else obj
        temporary = None
        try:
            temporary = value.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
            if temporary is None:
                raise RuntimeError("Object did not yield a mesh")
            for mat in temporary.materials:
                if mat:
                    materials[mat.as_pointer()] = mat
            metrics, world = _mesh_metrics(temporary, value.matrix_world, tolerance, max_vertices)
            record["mesh"] = metrics
            if not metrics["faces"]:
                issue("empty_mesh_geometry", obj.name, "review")
            if metrics.get("nonfinite_vertices"):
                issue("nonfinite_vertices", obj.name, "error", metrics["nonfinite_vertices"])
                report["coverage"]["mesh_topology"] = "partial"
                report["coverage"]["exact_face_signatures"] = "partial"
                report["coverage"]["near_vertex_candidates"] = "partial"
                continue
            for key in ("zero_area_faces", "zero_length_edges", "loose_edges", "loose_vertices",
                        "nonmanifold_edges", "inconsistent_winding_edges"):
                if metrics[key]:
                    issue(key, obj.name, "error", metrics[key])
            for key in ("boundary_edges", "inward_shell_candidates", "ambiguous_closed_shells"):
                if metrics[key]:
                    issue(key, obj.name, "review", metrics[key])
            near = metrics["near_vertex_candidates"]
            if near["status"] != "checked":
                report["coverage"]["near_vertex_candidates"] = "partial"
            if near.get("count", 0):
                issue("near_vertex_candidates", obj.name, "review", near["count"])

            if indexed_faces + len(temporary.polygons) > max_faces:
                metrics["exact_face_signatures"] = {"status": "skipped", "reason": "asset face budget exceeded"}
                report["coverage"]["exact_face_signatures"] = "partial"
                continue
            local_signatures, duplicate_count, duplicate_sample = {}, 0, []
            for poly in temporary.polygons:
                signature = _signature([world[i] for i in poly.vertices], tolerance)
                if signature in local_signatures:
                    duplicate_count += 1
                    if len(duplicate_sample) < SAMPLE_LIMIT:
                        duplicate_sample.append([local_signatures[signature], poly.index])
                else:
                    local_signatures[signature] = poly.index
                previous = face_index.get(signature)
                if previous and previous[0] != obj.name:
                    cross_count += 1
                    if len(cross_sample) < SAMPLE_LIMIT:
                        cross_sample.append([previous[0], previous[1], obj.name, poly.index])
                else:
                    face_index.setdefault(signature, (obj.name, poly.index))
            indexed_faces += len(temporary.polygons)
            metrics["exact_face_signatures"] = {"status": "checked", "duplicate_faces": duplicate_count,
                                                 "sample": duplicate_sample}
            if duplicate_count:
                issue("duplicate_faces", obj.name, "error", duplicate_count)
        except Exception as exc:
            issue("mesh_audit_error", obj.name, "error", detail=f"{type(exc).__name__}: {exc}")
            for key in ("mesh_topology", "exact_face_signatures", "near_vertex_candidates"):
                report["coverage"][key] = "partial"
        finally:
            if temporary is not None:
                value.to_mesh_clear()

    report["coincident_faces_across_objects"] = {
        "status": report["coverage"]["exact_face_signatures"], "count": cross_count, "sample": cross_sample,
        "note": "Counts additional matching faces against one representative; intentional contact needs review.",
    }
    if cross_count:
        issue("coincident_faces_across_objects", root.name, "review", cross_count)
    image_result = _image_checks(materials)
    report["images"] = image_result
    for finding in image_result["findings"]:
        issue(finding["code"], finding["image"], "error" if finding["code"] == "missing_image" else "review", detail=finding)
        if finding["code"] == "image_sequence_review":
            report["coverage"]["external_images"] = "partial"
    severity = Counter(i["severity"] for i in report["issues"])
    report["summary"] = {"objects": len(entries), "meshes": sum(o[0].type == "MESH" for o in entries),
                         "max_depth": max(depth for _, depth in entries),
                         "error_findings": severity["error"], "review_findings": severity["review"]}
    report["status"] = "issues_found" if report["issues"] else "checks_complete"
    return _json_safe(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--base-mesh", action="store_true")
    parser.add_argument("--tolerance", type=float)
    parser.add_argument("--max-direct-children", type=int, default=24)
    parser.add_argument("--max-vertices", type=int, default=250_000)
    parser.add_argument("--max-faces", type=int, default=200_000)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    report = audit_asset(args.root, evaluated=not args.base_mesh, tolerance=args.tolerance,
                         max_direct_children=args.max_direct_children, max_vertices=args.max_vertices,
                         max_faces=args.max_faces)
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded + "\n", encoding="utf-8")
        print(json.dumps({"report": str(args.out.resolve()), "summary": report["summary"],
                          "asset_acceptance": report["asset_acceptance"]}, ensure_ascii=False))
    else:
        print(encoded)


if __name__ == "__main__":
    main()
