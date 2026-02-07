import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-spider-mech',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="canvas"></div>`,
  styles: [`:host{display:block;width:100vw;height:100vh;overflow:hidden;background:#000}.canvas{width:100%;height:100%}`],
})
export class SpiderMechComponent implements AfterViewInit, OnDestroy {
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
    this.camera.position.set(0, 5, 10);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(el.clientWidth, el.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 1.5, 0);
    this.controls.update();
  }
  private animate = (): void => {
    this.animId = requestAnimationFrame(this.animate);
    this.group.rotation.y += 0.004;
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

    // --- Central body (ellipsoid) ---
    const body = this.w(new THREE.SphereGeometry(1.0, 12, 8));
    body.scale.set(1.3, 0.7, 1.0);
    body.position.y = 2.5;
    root.add(body);

    // Abdomen (rear sphere)
    const abdomen = this.w(new THREE.SphereGeometry(0.8, 10, 8));
    abdomen.scale.set(1.0, 0.8, 1.3);
    abdomen.position.set(0, 2.3, -1.4);
    root.add(abdomen);

    // Abdomen segments (rings)
    for (let i = 0; i < 3; i++) {
      const ring = this.w(new THREE.TorusGeometry(0.55 - i * 0.1, 0.03, 6, 12));
      ring.position.set(0, 2.3, -1.0 - i * 0.4);
      ring.rotation.x = Math.PI / 2;
      root.add(ring);
    }

    // --- Head/Eye cluster ---
    const headMount = this.w(new THREE.SphereGeometry(0.45, 8, 8));
    headMount.position.set(0, 2.9, 1.0);
    root.add(headMount);

    // Multiple eyes (cluster of 6)
    const eyePositions = [
      [-0.2, 3.15, 1.2], [0.2, 3.15, 1.2],
      [-0.35, 3.0, 1.15], [0.35, 3.0, 1.15],
      [-0.15, 2.85, 1.3], [0.15, 2.85, 1.3],
    ];
    for (const [x, y, z] of eyePositions) {
      const eye = this.w(new THREE.SphereGeometry(0.1, 8, 8));
      eye.position.set(x, y, z);
      root.add(eye);
    }

    // Mandibles
    for (const side of [-1, 1]) {
      const mandible = this.w(new THREE.ConeGeometry(0.06, 0.5, 4));
      mandible.position.set(side * 0.25, 2.6, 1.35);
      mandible.rotation.x = -0.6;
      mandible.rotation.z = side * 0.3;
      root.add(mandible);
    }

    // --- Turret on top ---
    const turretBase = this.w(new THREE.CylinderGeometry(0.3, 0.35, 0.3, 8));
    turretBase.position.set(0, 3.25, 0);
    root.add(turretBase);

    const turretGun = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.8, 6));
    turretGun.position.set(0, 3.4, 0.5);
    turretGun.rotation.x = Math.PI / 2 - 0.2;
    root.add(turretGun);

    // Sensor dish
    const dish = this.w(new THREE.SphereGeometry(0.2, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2));
    dish.position.set(0, 3.45, -0.3);
    dish.rotation.x = Math.PI;
    root.add(dish);

    const dishPole = this.w(new THREE.CylinderGeometry(0.02, 0.02, 0.25, 4));
    dishPole.position.set(0, 3.55, -0.3);
    root.add(dishPole);

    // --- 8 Legs (4 per side) ---
    const legAngles = [
      { angle: 0.4, length: 1.0 },
      { angle: 1.0, length: 1.1 },
      { angle: 1.7, length: 1.0 },
      { angle: 2.3, length: 0.85 },
    ];

    for (const side of [-1, 1]) {
      for (const { angle, length } of legAngles) {
        this.buildLeg(root, side, angle, length);
      }
    }

    // --- Mechanical details ---
    // Hydraulic pistons on body
    for (let i = 0; i < 4; i++) {
      const piston = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.4, 4));
      const a = (i / 4) * Math.PI * 2;
      piston.position.set(Math.cos(a) * 0.8, 2.5, Math.sin(a) * 0.6);
      piston.rotation.z = Math.cos(a) * 0.5;
      root.add(piston);
    }

    return root;
  }

  private buildLeg(root: THREE.Group, side: number, fwdAngle: number, lengthMul: number): void {
    const baseX = side * 0.9;
    const baseZ = Math.cos(fwdAngle) * 0.6 - 0.2;
    const baseY = 2.5;

    // Coxa (hip joint)
    const coxa = this.w(new THREE.SphereGeometry(0.12, 6, 6));
    coxa.position.set(baseX, baseY, baseZ);
    root.add(coxa);

    // Femur (goes out and up)
    const femurLen = 1.2 * lengthMul;
    const femur = this.w(new THREE.CylinderGeometry(0.06, 0.05, femurLen, 6));
    const fX = baseX + side * femurLen * 0.45;
    const fY = baseY + 0.3;
    const fZ = baseZ + Math.cos(fwdAngle) * femurLen * 0.3;
    femur.position.set(fX, fY, fZ);
    femur.rotation.z = side * 1.1;
    femur.rotation.y = -fwdAngle * side * 0.3;
    root.add(femur);

    // Knee joint
    const kneeX = baseX + side * femurLen * 0.9;
    const kneeY = baseY + 0.5;
    const kneeZ = baseZ + Math.cos(fwdAngle) * femurLen * 0.6;
    const knee = this.w(new THREE.SphereGeometry(0.1, 6, 6));
    knee.position.set(kneeX, kneeY, kneeZ);
    root.add(knee);

    // Tibia (goes down to ground)
    const tibiaLen = 1.8 * lengthMul;
    const tibia = this.w(new THREE.CylinderGeometry(0.05, 0.03, tibiaLen, 6));
    const tX = kneeX + side * 0.3;
    const tY = kneeY - tibiaLen * 0.45;
    const tZ = kneeZ + Math.cos(fwdAngle) * 0.4;
    tibia.position.set(tX, tY, tZ);
    tibia.rotation.z = side * 0.2;
    tibia.rotation.y = -fwdAngle * side * 0.2;
    root.add(tibia);

    // Foot tip (small cone)
    const foot = this.w(new THREE.ConeGeometry(0.05, 0.15, 4));
    foot.position.set(tX + side * 0.15, tY - tibiaLen * 0.45, tZ + Math.cos(fwdAngle) * 0.2);
    foot.rotation.x = Math.PI;
    root.add(foot);
  }
}
