import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-skull',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="canvas"></div>`,
  styles: [`:host{display:block;width:100vw;height:100vh;overflow:hidden;background:#000}.canvas{width:100%;height:100%}`],
})
export class SkullComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animId = 0;
  private group!: THREE.Group;

  ngAfterViewInit(): void {
    this.initScene();
    this.group = this.build();
    this.scene.add(this.group);
    this.animate();
    window.addEventListener('resize', this.onResize);
  }
  ngOnDestroy(): void {
    cancelAnimationFrame(this.animId);
    window.removeEventListener('resize', this.onResize);
    this.controls.dispose();
    this.renderer.dispose();
  }

  private initScene(): void {
    const el = this.container.nativeElement;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);
    this.camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 100);
    this.camera.position.set(0, 0, 8);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(el.clientWidth, el.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 0.5, 0);
    this.controls.update();
  }
  private animate = (): void => {
    this.animId = requestAnimationFrame(this.animate);
    this.group.rotation.y += 0.003;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };
  private onResize = (): void => {
    const el = this.container.nativeElement;
    this.camera.aspect = el.clientWidth / el.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(el.clientWidth, el.clientHeight);
  };

  private m(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  }
  private w(g: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(g, this.m());
  }

  private build(): THREE.Group {
    const root = new THREE.Group();

    // --- Cranium (main skull dome) ---
    const cranium = this.w(new THREE.SphereGeometry(1.5, 14, 12, 0, Math.PI * 2, 0, Math.PI * 0.75));
    cranium.position.y = 1.0;
    root.add(cranium);

    // Back of skull (slightly flattened)
    const backSkull = this.w(new THREE.SphereGeometry(1.4, 12, 10));
    backSkull.scale.set(1.0, 0.95, 0.9);
    backSkull.position.set(0, 0.8, -0.2);
    root.add(backSkull);

    // --- Brow ridge ---
    const browRidge = this.w(new THREE.TorusGeometry(1.1, 0.12, 6, 16, Math.PI));
    browRidge.position.set(0, 1.0, 0.7);
    browRidge.rotation.x = 0.1;
    root.add(browRidge);

    // --- Eye sockets (larger, deeper) ---
    for (const side of [-1, 1]) {
      // Socket ring
      const socket = this.w(new THREE.TorusGeometry(0.38, 0.06, 8, 12));
      socket.position.set(side * 0.55, 0.9, 1.05);
      root.add(socket);

      // Eyeball inside socket
      const eyeball = this.w(new THREE.SphereGeometry(0.25, 8, 8));
      eyeball.position.set(side * 0.55, 0.9, 0.9);
      root.add(eyeball);

      // Pupil
      const pupil = this.w(new THREE.SphereGeometry(0.1, 6, 6));
      pupil.position.set(side * 0.55, 0.9, 1.15);
      root.add(pupil);
    }

    // --- Nose cavity ---
    const noseHole = this.w(new THREE.ConeGeometry(0.2, 0.4, 3));
    noseHole.position.set(0, 0.45, 1.2);
    noseHole.rotation.x = -0.1;
    root.add(noseHole);

    // Nasal bridge
    const nasalBridge = this.w(new THREE.BoxGeometry(0.15, 0.5, 0.15, 1, 2, 1));
    nasalBridge.position.set(0, 0.75, 1.2);
    root.add(nasalBridge);

    // --- Cheekbones ---
    for (const side of [-1, 1]) {
      const cheek = this.w(new THREE.SphereGeometry(0.3, 8, 6));
      cheek.scale.set(1.2, 0.7, 0.8);
      cheek.position.set(side * 0.85, 0.5, 0.8);
      root.add(cheek);

      // Zygomatic arch
      const arch = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.7, 6));
      arch.rotation.z = side * 0.3;
      arch.rotation.y = side * 0.5;
      arch.position.set(side * 1.1, 0.55, 0.4);
      root.add(arch);
    }

    // --- Upper jaw / Maxilla ---
    const maxilla = this.w(new THREE.BoxGeometry(1.4, 0.4, 0.9, 3, 1, 2));
    maxilla.position.set(0, 0.05, 0.7);
    root.add(maxilla);

    // --- Lower jaw / Mandible ---
    const mandible = this.w(new THREE.BoxGeometry(1.2, 0.35, 0.8, 3, 1, 2));
    mandible.position.set(0, -0.35, 0.65);
    root.add(mandible);

    // Jaw hinge points
    for (const side of [-1, 1]) {
      const hinge = this.w(new THREE.SphereGeometry(0.1, 6, 6));
      hinge.position.set(side * 0.75, -0.1, 0.3);
      root.add(hinge);

      // Mandible ramus (vertical part of jaw)
      const ramus = this.w(new THREE.BoxGeometry(0.12, 0.5, 0.3, 1, 2, 1));
      ramus.position.set(side * 0.65, -0.1, 0.4);
      root.add(ramus);
    }

    // Chin
    const chin = this.w(new THREE.SphereGeometry(0.18, 8, 6));
    chin.position.set(0, -0.5, 0.9);
    root.add(chin);

    // --- Teeth (upper row) ---
    for (let i = 0; i < 8; i++) {
      const x = -0.5 + i * 0.145;
      const isCanine = i === 1 || i === 6;
      const h = isCanine ? 0.25 : 0.18;
      const tooth = this.w(new THREE.BoxGeometry(0.1, h, 0.1, 1, 1, 1));
      tooth.position.set(x, -0.08, 1.05 + Math.sin((i / 7) * Math.PI) * 0.15);
      root.add(tooth);
    }

    // --- Teeth (lower row) ---
    for (let i = 0; i < 7; i++) {
      const x = -0.43 + i * 0.145;
      const tooth = this.w(new THREE.BoxGeometry(0.09, 0.15, 0.09, 1, 1, 1));
      tooth.position.set(x, -0.22, 1.0 + Math.sin((i / 6) * Math.PI) * 0.12);
      root.add(tooth);
    }

    // --- Temporal region detail ---
    for (const side of [-1, 1]) {
      const temporal = this.w(new THREE.SphereGeometry(0.4, 6, 6));
      temporal.scale.set(0.5, 0.8, 0.7);
      temporal.position.set(side * 1.3, 0.7, 0);
      root.add(temporal);
    }

    // --- Suture lines on cranium ---
    // Sagittal suture (top, front to back)
    const sagittal = this.w(new THREE.TorusGeometry(1.5, 0.02, 4, 20, Math.PI * 0.6));
    sagittal.position.set(0, 1.05, 0);
    sagittal.rotation.set(0, Math.PI / 2, Math.PI / 2);
    root.add(sagittal);

    // Coronal suture (side to side)
    const coronal = this.w(new THREE.TorusGeometry(1.4, 0.02, 4, 20, Math.PI * 0.5));
    coronal.position.set(0, 1.0, 0.3);
    coronal.rotation.set(Math.PI / 2, 0, 0);
    root.add(coronal);

    // --- Foramen magnum (base of skull opening) ---
    const foramen = this.w(new THREE.TorusGeometry(0.35, 0.04, 6, 12));
    foramen.position.set(0, -0.3, -0.5);
    foramen.rotation.x = Math.PI / 2 + 0.3;
    root.add(foramen);

    // Spine connector
    const spineTop = this.w(new THREE.CylinderGeometry(0.15, 0.2, 0.4, 8));
    spineTop.position.set(0, -0.65, -0.5);
    root.add(spineTop);

    return root;
  }
}
