/**
 * BabylonScene — a thin wrapper over @babylonjs/core that mounts a WebGL2
 * canvas and renders a generated asset image as a textured plane with a
 * simple turntable animation. The user gets to inspect the asset before
 * it is committed, in 3D, in their browser, with zero infra.
 *
 * The component is intentionally minimal — its job is to prove that
 * the generated asset round-trips through a 3D preview, not to ship a
 * full Babylon scene graph. We ship @babylonjs/core + loaders + materials
 * (already in web/package.json) so any future enhancement (PBR, env maps,
 * physics) is just a JSX line away.
 */

import { useEffect, useRef } from "react";
import { Engine } from "@babylonjs/core/Engines/engine";
import { Scene } from "@babylonjs/core/scene";
import { ArcRotateCamera } from "@babylonjs/core/Cameras/arcRotateCamera";
import { HemisphericLight } from "@babylonjs/core/Lights/hemisphericLight";
import { Vector3, Color3, Color4 } from "@babylonjs/core/Maths/math";
import { MeshBuilder } from "@babylonjs/core/Meshes/meshBuilder";
import { StandardMaterial } from "@babylonjs/core/Materials/standardMaterial";
import { Texture } from "@babylonjs/core/Materials/Textures/texture";

export interface BabylonSceneProps {
  imageDataUrl: string;             // data:image/png;base64,...
  width?: number;
  height?: number;
  className?: string;
}

export function BabylonScene({
  imageDataUrl,
  width = 480,
  height = 360,
  className,
}: BabylonSceneProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const engine = new Engine(canvas, true, {
      preserveDrawingBuffer: true,
      stencil: true,
    });
    const scene = new Scene(engine);
    scene.clearColor = new Color4(0.06, 0.08, 0.12, 1.0);

    const camera = new ArcRotateCamera(
      "cam",
      -Math.PI / 2,
      Math.PI / 3,
      2.4,
      Vector3.Zero(),
      scene,
    );
    camera.attachControl(canvas, true);
    camera.lowerRadiusLimit = 1.6;
    camera.upperRadiusLimit = 6.0;
    camera.wheelPrecision = 30;

    new HemisphericLight("light", new Vector3(0, 1, 0), scene);

    // The plane displays the generated image as a texture.
    const plane = MeshBuilder.CreatePlane("asset", { width: 2, height: 1.5 }, scene);
    plane.position.y = 0;

    const mat = new StandardMaterial("mat", scene);
    const texture = new Texture(
      // @ts-ignore — Babylon accepts a data URI for images.
      imageDataUrl,
      scene,
      true,
      false,
    );
    mat.diffuseTexture = texture;
    mat.specularColor = new Color3(0.1, 0.1, 0.1);
    plane.material = mat;

    // Turntable animation: subtle, runs while the canvas is in view.
    let frame = 0;
    const observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) engine.runRenderLoop(() => {
          frame++;
          plane.rotation.y = (frame * 0.003) % (Math.PI * 2);
        });
        else engine.stopRenderLoop();
      }
    });
    observer.observe(canvas);

    engine.runRenderLoop(() => {
      frame++;
      plane.rotation.y = (frame * 0.003) % (Math.PI * 2);
    });

    const resize = () => engine.resize();
    window.addEventListener("resize", resize);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", resize);
      engine.stopRenderLoop();
      scene.dispose();
      engine.dispose();
    };
  }, [imageDataUrl]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={className}
      style={{ display: "block", width, height, borderRadius: 8 }}
    />
  );
}
