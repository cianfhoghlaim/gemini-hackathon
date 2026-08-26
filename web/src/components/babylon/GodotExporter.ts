/**
 * GodotExporter — produces a `.tscn` (Godot scene) for an asset, with
 * the asset image as a Sprite3D texture. The user can drop the file into
 * their Godot project and get the asset rendered in 3D in the canonical
 * Godot scene graph.
 *
 * Why Godot: the parent monorepo's `docs/research/game/GRAPHICS_INDEX.md`
 * points at Godot as the canonical engine for the project, and the
 * existing architecture uses Godot 4.4 + Rust gdext. Exporting to Godot
 * keeps the pipeline consistent with the rest of the platform.
 *
 * The export is a pure-Python function that returns the file contents —
 * the web app can either download it via a Blob or POST it to a Cloud
 * Run endpoint that pipes it to GCS.
 */

import type { AssetControlRecord } from "gemini_hackathon/assets/control_record";

export interface GodotExportOptions {
  texturePath: string;
  nodeName?: string;
  position?: { x: number; y: number; z?: number };
}

/**
 * Build the .tscn file text. Pure function — does not touch disk.
 */
export function buildGodotSceneText(
  control: AssetControlRecord,
  opts: GodotExportOptions,
): string {
  const nodeName = (opts.nodeName ?? "AssetSprite").replace(/[^A-Za-z0-9_]/g, "_");
  const x = opts.position?.x ?? 0;
  const y = opts.position?.y ?? 0;

  const lines: string[] = [
    "[gd_scene load_steps=2 format=3]",
    "",
    "[ext_resource type=\"Texture2D\" path=\"" + escape(control.source_pdf_path || opts.texturePath) + "\" id=\"1_\"]",
    "",
    "[sub_resource type=\"StandardMaterial3D\" id=\"StandardMaterial3D_1\"]",
    "resource_local_to_scene = false",
    "resource_name = \"asset_material\"",
    "albedo_color = Color(1, 1, 1, 1)",
    "albedo_texture = ExtResource(\"1_\")",
    "",
    "[node name=\"" + nodeName + "\" type=\"Sprite3D\"]",
    "material_override = SubResource(\"StandardMaterial3D_1\")",
    "texture = ExtResource(\"1_\")",
    "position = Vector3(" + x + ", " + y + ", 0)",
    "",
    "[node name=\"AssetCamera\" type=\"Camera3D\" parent=\".\"]",
    "transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 3)",
    "",
    "[node name=\"AssetLight\" type=\"DirectionalLight3D\" parent=\".\"]",
    "transform = Transform3D(0.866, -0.354, 0.354, 0, 0.707, 0.707, 0.5, 0.612, -0.612, 0, 2, 3)",
    "",
    "[editable]",
    "",
  ];
  return lines.join("\n");
}

function escape(s: string): string {
  return s.replace(/\\/g, "\\\\").replace(/"/g, "\\\"");
}

/**
 * Build a Blob URL for browser download.
 */
export function godotDownloadUrl(control: AssetControlRecord, opts: GodotExportOptions): string {
  const text = buildGodotSceneText(control, opts);
  const blob = new Blob([text], { type: "text/plain" });
  return URL.createObjectURL(blob);
}
