"""Isolated Blender regression fixtures for this skill's read-only auditor.

Use --background --factory-startup. Never run inside the user's live Blender.
Creation requires a new/empty output directory; verification reads those fixtures
in a fresh process. No existing project files are opened or overwritten.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector


SCRIPTS = Path(__file__).resolve().parent
audit = runpy.run_path(str(SCRIPTS / "audit_asset.py"))["audit_asset"]
CUBE_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
              (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def box_geometry(size, center=(0., 0., 0.)):
    sx, sy, sz = (n / 2 for n in size)
    points = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
              (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    return [tuple(p[i] + center[i] for i in range(3)) for p in points], CUBE_FACES


def mesh_object(name, vertices, faces, parent=None, edges=()):
    data = bpy.data.meshes.new(name + "_Mesh")
    data.from_pydata(vertices, edges, faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def box(name, parent=None, size=(1., 1., 1.), center=(0., 0., 0.), inverted=False):
    points, faces = box_geometry(size, center)
    if inverted:
        faces = [tuple(reversed(face)) for face in faces]
    return mesh_object(name, points, faces, parent)


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def codes(report):
    return {entry["code"] for entry in report["issues"]}


def measured(obj_name, **kwargs):
    bpy.context.view_layer.update()
    return audit(obj_name, **kwargs)


def snapshot():
    objects = []
    for obj in bpy.context.scene.objects:
        item = {"name": obj.name, "parent": obj.parent.name if obj.parent else None,
                "matrix": [list(row) for row in obj.matrix_world], "selected": obj.select_get(),
                "hide_viewport": obj.hide_viewport, "hide_render": obj.hide_render,
                "modifiers": [(m.name, m.type, m.show_viewport, m.show_render) for m in obj.modifiers],
                "material_slots": [m.material.name if m.material else None for m in obj.material_slots]}
        if obj.type == "MESH":
            item["vertices"] = [list(v.co) for v in obj.data.vertices]
            item["faces"] = [list(p.vertices) for p in obj.data.polygons]
            item["edges"] = [list(e.vertices) for e in obj.data.edges]
        objects.append(item)
    active = bpy.context.view_layer.objects.active
    encoded = json.dumps({"objects": objects, "active": active.name if active else None,
                          "mode": bpy.context.mode, "filepath": bpy.data.filepath,
                          "datablock_counts": [len(bpy.data.objects), len(bpy.data.meshes), len(bpy.data.materials)]},
                         sort_keys=True, allow_nan=True)
    return hashlib.sha256(encoded.encode()).hexdigest()


def create_delivery_fixture():
    root = empty("QA_Cabinet")
    root["industrial_role"] = "assembly"
    vertices, faces = [], []
    panels = [((1.2, .8, .10), (0, 0, .05)), ((1.2, .8, .10), (0, 0, 1.75)),
              ((.08, .8, 1.60), (-.56, 0, .90)), ((.08, .8, 1.60), (.56, 0, .90)),
              ((1.04, .08, 1.60), (0, .36, .90))]
    for size, center in panels:
        verts, fs = box_geometry(size, center)
        offset = len(vertices)
        vertices.extend(verts)
        faces.extend(tuple(i + offset for i in f) for f in fs)
    body = mesh_object("QA_Body", vertices, faces, root)
    body["industrial_role"] = "static"
    # Door's local origin is on its hinge, not its geometric center.
    door = box("QA_Door", root, (.98, .05, 1.52), (.49, 0, 0))
    door.location = (-.49, -.43, .90)
    door["industrial_role"] = "motion"
    door["motion_type"] = "rotation"
    door["motion_axis"] = "Z"
    for obj, color in [(body, (.20, .26, .33, 1.)), (door, (.95, .33, .06, 1.))]:
        mat = bpy.data.materials.new(obj.name + "_Finish")
        mat.diffuse_color = color
        mat.use_nodes = True
        node = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        node.inputs["Base Color"].default_value = color
        node.inputs["Roughness"].default_value = .38
        obj.data.materials.append(mat)
    bpy.context.view_layer.update()
    return root, body, door


def render_fixture(out_dir):
    camera_data = bpy.data.cameras.new("QA_ReviewCamera")
    camera = bpy.data.objects.new("QA_ReviewCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (3., -4., 2.8)
    camera.rotation_euler = (Vector((0., 0., .9)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.7
    scene = bpy.context.scene
    scene.camera = camera
    try:
        scene.render.engine = "BLENDER_WORKBENCH"
    except TypeError as exc:
        return {"status": "skipped", "reason": str(exc)}
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(out_dir / "fixture_review.png")
    bpy.ops.render.render(write_still=True)
    return {"status": "rendered_not_yet_visually_reviewed", "path": scene.render.filepath}


def run_fixtures(out_dir):
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError("Use a new or empty directory; existing assets are never overwritten")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".industrial_skill_test").write_text("isolated-regression-fixture-v1\n")
    scene = bpy.data.scenes.new("IndustrialSkillRegression")
    bpy.context.window.scene = scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.
    results = []

    def check(name, condition, detail=None):
        results.append({"name": name, "passed": bool(condition), "detail": detail})

    clean = empty("CleanAsset")
    body = box("RigidBody", clean)
    door = box("MovingDoor", clean, size=(.8, .05, .8))
    door.location.y = -.6
    report = measured(clean.name)
    check("clean_closed_rigid_and_motion_parts", not report["issues"], report["issues"])
    bpy.context.view_layer.objects.active = door
    door.select_set(True)
    before = snapshot()
    measured(clean.name)
    check("audit_preserves_scene_and_selection", snapshot() == before)

    dup = empty("DuplicateAsset")
    points, faces = box_geometry((1., 1., 1.))
    obj = mesh_object("DuplicatedShells", points + points,
                      list(faces) + [tuple(i + 8 for i in f) for f in faces], dup)
    report = measured(dup.name)
    metrics = next(r["mesh"] for r in report["objects"] if r["name"] == obj.name)
    check("detect_coincident_faces_with_distinct_vertex_indices",
          metrics["exact_face_signatures"]["duplicate_faces"] == 6 and "near_vertex_candidates" in codes(report))

    cross = empty("CrossObjectAsset")
    box("CoincidentA", cross)
    box("CoincidentB", cross)
    check("detect_cross_object_duplicate_surfaces", measured(cross.name)["coincident_faces_across_objects"]["count"] == 6)
    inward = box("InwardShell", inverted=True)
    check("detect_inverted_closed_shell", "inward_shell_candidates" in codes(measured(inward.name)))
    mirrored = box("ReflectedShell")
    mirrored.scale.x = -1
    report = measured(mirrored.name)
    check("distinguish_reflection_from_inverted_source", "negative_world_determinant" in codes(report)
          and "inward_shell_candidates" not in codes(report))
    degenerate = mesh_object("CollapsedFace", [(0, 0, 0), (1, 0, 0), (2, 0, 0), (4, 4, 4)], [(0, 1, 2)])
    report = measured(degenerate.name)
    check("detect_degenerate_face_and_loose_vertex", {"zero_area_faces", "loose_vertices"} <= codes(report))
    thin = mesh_object("IntentionalSheet", [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [(0, 1, 2, 3)])
    report = measured(thin.name)
    check("open_sheet_is_review_not_automatic_error", report["summary"]["error_findings"] == 0 and "boundary_edges" in codes(report))
    solidify = thin.modifiers.new("Thickness", "SOLIDIFY")
    solidify.thickness = .05
    report = measured(thin.name)
    check("audit_evaluated_modifier_geometry", "boundary_edges" not in codes(report)
          and len(thin.data.polygons) == 1 and next(o["mesh"] for o in report["objects"] if "mesh" in o)["faces"] > 1)

    wide = empty("OverlyFlatHierarchy")
    for i in range(7):
        child = box(f"FixedDetail_{i}", wide, size=(.1, .1, .1))
        child.location.x = i * .2
    check("detect_excessive_direct_children", "hierarchy_fanout_review" in codes(measured(wide.name, max_direct_children=5)))
    chain = empty("WarehouseRoot")
    storage = box("WarehouseFixed", chain)
    motion = empty("StackerComponent", chain)
    for name in ("Travel_X", "Lift_Z", "Fork_Y1", "Fork_Y2"):
        motion = empty(name, motion)
    end = box("ForkGeometry", motion, (.2, .8, .08))
    report = measured(chain.name)
    fixed_before = storage.matrix_world.copy()
    end_before = end.matrix_world.translation.copy()
    bpy.data.objects["Travel_X"].location.x += 2.
    bpy.context.view_layer.update()
    check("nested_motion_preserves_fixed_branch", (storage.matrix_world.translation - fixed_before.translation).length < 1e-7
          and abs(end.matrix_world.translation.x - end_before.x - 2.) < 1e-6 and report["summary"]["max_depth"] == 6)
    limited = measured(clean.name, max_vertices=2, max_faces=1)
    check("budget_skips_are_visible", limited["coverage"]["near_vertex_candidates"] == "partial"
          and limited["coverage"]["exact_face_signatures"] == "partial" and limited["asset_acceptance"] == "not_determined")
    bad = box("NonfiniteMesh")
    bad.data.vertices[0].co.x = float("nan")
    report = measured(bad.name)
    check("nonfinite_input_report_is_serializable", "nonfinite_vertices" in codes(report)
          and bool(json.dumps(report, allow_nan=False)))
    blank = mesh_object("EmptyMesh", [], [])
    check("empty_mesh_does_not_crash", "mesh_audit_error" not in codes(measured(blank.name)))
    invalid_transform = box("NonfiniteTransform")
    invalid_transform.location.x = float("nan")
    report = measured(invalid_transform.name)
    check("invalid_transform_skips_are_explicit", "nonfinite_transform" in codes(report)
          and all(report["coverage"][key] == "partial"
                  for key in ("mesh_topology", "exact_face_signatures", "near_vertex_candidates"))
          and bool(json.dumps(report, allow_nan=False)))

    mat = bpy.data.materials.new("MissingTextureMaterial")
    mat.use_nodes = True
    image = bpy.data.images.new("AbsentExternalTexture", 8, 8)
    image.source = "FILE"
    image.filepath = str(out_dir / "intentionally_absent_texture.png")
    mat.node_tree.nodes.new("ShaderNodeTexImage").image = image
    body.data.materials.append(mat)
    check("detect_missing_external_image", "missing_image" in codes(measured(clean.name)))

    # Separate scene keeps diagnostic objects out of the selected export.
    fixture_scene = bpy.data.scenes.new("DeliveryFixture")
    bpy.context.window.scene = fixture_scene
    fixture_scene.unit_settings.system = "METRIC"
    fixture_scene.unit_settings.scale_length = 1.
    root, body, door = create_delivery_fixture()
    report = measured(root.name)
    check("delivery_fixture_has_clean_compact_hierarchy", report["summary"]["error_findings"] == 0
          and report["summary"]["objects"] == 3 and report["summary"]["max_depth"] == 1)
    (out_dir / "fixture_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    expected = {"root": root.name, "parents": {body.name: root.name, door.name: root.name},
                "bounds": report["bounds_world"], "door_pivot": list(door.matrix_world.translation),
                "door_vertex_world": list(door.matrix_world @ door.data.vertices[0].co)}
    door.rotation_euler.z = math.radians(60)
    bpy.context.view_layer.update()
    expected["door_vertex_world_open"] = list(door.matrix_world @ door.data.vertices[0].co)
    door.rotation_euler.z = 0.
    bpy.context.view_layer.update()
    (out_dir / "roundtrip_expected.json").write_text(json.dumps(expected, indent=2) + "\n")
    for item in fixture_scene.objects:
        item.select_set(item in {root, body, door})
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(filepath=str(out_dir / "fixture.fbx"), use_selection=True,
                             object_types={"EMPTY", "MESH"}, bake_anim=False,
                             apply_unit_scale=True, axis_forward="-Z", axis_up="Y")
    check("fbx_file_created", (out_dir / "fixture.fbx").stat().st_size > 0)
    preview = render_fixture(out_dir)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / "fixture.blend"))
    payload = {"blender_version": bpy.app.version_string, "tests": results,
               "passed": sum(x["passed"] for x in results), "failed": sum(not x["passed"] for x in results),
               "preview": preview, "live_mcp_tested": False, "real_reference_modeling_tested": False}
    (out_dir / "self_test_report.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload))
    if payload["failed"]:
        raise AssertionError("One or more isolated fixture checks failed")


def verify_roundtrip(out_dir):
    if not (out_dir / ".industrial_skill_test").is_file():
        raise ValueError("Not an isolated self-test directory")
    expected = json.loads((out_dir / "roundtrip_expected.json").read_text())
    scene = bpy.data.scenes.new("FreshFBXReadback")
    bpy.context.window.scene = scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.
    bpy.ops.import_scene.fbx(filepath=str(out_dir / "fixture.fbx"))
    report = measured(expected["root"])
    checks = []

    def check(name, passed, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("one_root_two_meshes_no_presentation_objects", len(scene.objects) == 3
          and len([o for o in scene.objects if o.parent is None]) == 1
          and {o.type for o in scene.objects} == {"MESH", "EMPTY"})
    check("stable_parent_paths", all(scene.objects.get(name) and scene.objects[name].parent
          and scene.objects[name].parent.name == parent for name, parent in expected["parents"].items()))
    errors = [abs(a - b) for key in ("min", "max")
              for a, b in zip(expected["bounds"][key], report["bounds_world"][key])]
    check("meter_scale_and_geometry_bounds", max(errors) < 1e-5, {"max_error_m": max(errors)})
    door = scene.objects["QA_Door"]
    pivot_error = (door.matrix_world.translation - Vector(expected["door_pivot"])).length
    check("door_pivot_preserved", pivot_error < 1e-5, {"error_m": pivot_error})
    original_point = Vector(expected["door_vertex_world"])
    vertex = min(door.data.vertices, key=lambda v: (door.matrix_world @ v.co - original_point).length)
    body_before = scene.objects["QA_Body"].matrix_world.copy()
    door.rotation_euler.z += math.radians(60)
    bpy.context.view_layer.update()
    open_error = (door.matrix_world @ vertex.co - Vector(expected["door_vertex_world_open"])).length
    body_error = max(abs(a - b) for ra, rb in zip(body_before, scene.objects["QA_Body"].matrix_world) for a, b in zip(ra, rb))
    check("door_motion_and_fixed_body", open_error < 1e-5 and body_error < 1e-7,
          {"moving_vertex_error_m": open_error, "fixed_transform_error": body_error})
    check("material_slots_survive", all(len(scene.objects[name].data.materials) == 1 for name in expected["parents"]))
    check("no_geometry_errors_after_import", report["summary"]["error_findings"] == 0, report["issues"])
    bpy.ops.wm.open_mainfile(filepath=str(out_dir / "fixture.blend"), load_ui=False)
    source_report = measured(expected["root"])
    source_error = max(abs(a - b) for key in ("min", "max")
                       for a, b in zip(expected["bounds"][key], source_report["bounds_world"][key]))
    check("editable_blend_reopens_with_original_geometry", source_report["summary"]["objects"] == 3
          and source_report["summary"]["error_findings"] == 0 and source_error < 1e-7)
    payload = {"blender_version": bpy.app.version_string, "tests": checks,
               "passed": sum(x["passed"] for x in checks), "failed": sum(not x["passed"] for x in checks),
               "target_engine_tested": False}
    (out_dir / "roundtrip_report.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload))
    if payload["failed"]:
        raise AssertionError("Independent FBX readback failed")


def main():
    if not bpy.app.background or bpy.data.filepath:
        raise RuntimeError("Self-test requires a fresh background Blender with no user file loaded")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--verify-roundtrip", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.verify_roundtrip:
        verify_roundtrip(args.out_dir.resolve())
    else:
        run_fixtures(args.out_dir.resolve())


if __name__ == "__main__":
    main()
