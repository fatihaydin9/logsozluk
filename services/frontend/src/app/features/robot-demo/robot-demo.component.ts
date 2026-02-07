import {
  Component,
  ElementRef,
  ViewChild,
  AfterViewInit,
  OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-robot-demo',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="robot-canvas"></div>`,
  styles: [
    `
      :host {
        display: block;
        width: 100vw;
        height: 100vh;
        overflow: hidden;
        background: #000;
      }
      .robot-canvas {
        width: 100%;
        height: 100%;
      }
    `,
  ],
})
export class RobotDemoComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) container!: ElementRef<HTMLDivElement>;

  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animationId = 0;
  private robot!: THREE.Group;

  ngAfterViewInit(): void {
    this.initScene();
    this.robot = this.buildRobot();
    this.scene.add(this.robot);
    this.animate();
    window.addEventListener('resize', this.onResize);
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.animationId);
    window.removeEventListener('resize', this.onResize);
    this.controls.dispose();
    this.renderer.dispose();
  }

  /* ------------------------------------------------------------------ */
  /*  Scene setup                                                        */
  /* ------------------------------------------------------------------ */

  private initScene(): void {
    const el = this.container.nativeElement;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);

    this.camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 100);
    this.camera.position.set(0, 2, 10);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(el.clientWidth, el.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 1.5, 0);
    this.controls.update();
  }

  /* ------------------------------------------------------------------ */
  /*  Animation loop                                                     */
  /* ------------------------------------------------------------------ */

  private animate = (): void => {
    this.animationId = requestAnimationFrame(this.animate);
    this.robot.rotation.y += 0.003;
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };

  private onResize = (): void => {
    const el = this.container.nativeElement;
    this.camera.aspect = el.clientWidth / el.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(el.clientWidth, el.clientHeight);
  };

  /* ------------------------------------------------------------------ */
  /*  Material helper                                                    */
  /* ------------------------------------------------------------------ */

  private mat(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  }

  private wire(geo: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(geo, this.mat());
  }

  /* ------------------------------------------------------------------ */
  /*  Robot builder                                                      */
  /* ------------------------------------------------------------------ */

  private buildRobot(): THREE.Group {
    const robot = new THREE.Group();

    robot.add(this.buildHead());
    robot.add(this.buildBody());
    robot.add(this.buildArm(1));   // right arm
    robot.add(this.buildArm(-1));  // left arm
    robot.add(this.buildLeg(0.5));  // right leg
    robot.add(this.buildLeg(-0.5)); // left leg
    robot.add(this.buildWindUpKey());

    return robot;
  }

  /* --- Head --------------------------------------------------------- */

  private buildHead(): THREE.Group {
    const head = new THREE.Group();
    head.position.y = 3.6;

    // main head box
    const skull = this.wire(new THREE.BoxGeometry(1.4, 1.0, 1.0, 3, 2, 2));
    head.add(skull);

    // dome on top
    const dome = this.wire(new THREE.SphereGeometry(0.7, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2));
    dome.position.y = 0.5;
    head.add(dome);

    // antenna base
    const antennaBase = this.wire(new THREE.CylinderGeometry(0.08, 0.08, 0.4, 6));
    antennaBase.position.y = 1.1;
    head.add(antennaBase);

    // antenna ball
    const antennaBall = this.wire(new THREE.SphereGeometry(0.12, 6, 6));
    antennaBall.position.y = 1.4;
    head.add(antennaBall);

    // left eye
    const leftEye = this.wire(new THREE.SphereGeometry(0.15, 8, 8));
    leftEye.position.set(-0.3, 0.1, 0.5);
    head.add(leftEye);

    // right eye
    const rightEye = this.wire(new THREE.SphereGeometry(0.15, 8, 8));
    rightEye.position.set(0.3, 0.1, 0.5);
    head.add(rightEye);

    // mouth grille (horizontal bars)
    for (let i = 0; i < 3; i++) {
      const bar = this.wire(new THREE.BoxGeometry(0.6, 0.04, 0.06, 2, 1, 1));
      bar.position.set(0, -0.2 - i * 0.1, 0.5);
      head.add(bar);
    }

    // ears
    for (const side of [-1, 1]) {
      const ear = this.wire(new THREE.CylinderGeometry(0.15, 0.15, 0.15, 8));
      ear.rotation.z = Math.PI / 2;
      ear.position.set(side * 0.8, 0.1, 0);
      head.add(ear);
    }

    return head;
  }

  /* --- Body / Torso ------------------------------------------------- */

  private buildBody(): THREE.Group {
    const body = new THREE.Group();
    body.position.y = 2.0;

    // main torso
    const torso = this.wire(new THREE.BoxGeometry(1.8, 2.0, 1.0, 4, 4, 2));
    body.add(torso);

    // chest clock (torus)
    const clock = this.wire(new THREE.TorusGeometry(0.3, 0.04, 8, 16));
    clock.position.set(0, 0.3, 0.51);
    body.add(clock);

    // clock hands
    const hourHand = this.wire(new THREE.BoxGeometry(0.03, 0.2, 0.03));
    hourHand.position.set(0, 0.35, 0.55);
    hourHand.rotation.z = Math.PI / 6;
    body.add(hourHand);

    const minHand = this.wire(new THREE.BoxGeometry(0.02, 0.28, 0.02));
    minHand.position.set(0, 0.35, 0.55);
    minHand.rotation.z = -Math.PI / 3;
    body.add(minHand);

    // buttons on belly
    for (let i = 0; i < 3; i++) {
      const btn = this.wire(new THREE.CylinderGeometry(0.08, 0.08, 0.06, 8));
      btn.rotation.x = Math.PI / 2;
      btn.position.set(-0.25 + i * 0.25, -0.4, 0.51);
      body.add(btn);
    }

    // belt
    const belt = this.wire(new THREE.BoxGeometry(1.85, 0.15, 1.05, 4, 1, 2));
    belt.position.y = -0.9;
    body.add(belt);

    // belt buckle
    const buckle = this.wire(new THREE.BoxGeometry(0.3, 0.2, 0.1));
    buckle.position.set(0, -0.9, 0.55);
    body.add(buckle);

    return body;
  }

  /* --- Arm ---------------------------------------------------------- */

  private buildArm(side: number): THREE.Group {
    const arm = new THREE.Group();

    // shoulder joint
    const shoulder = this.wire(new THREE.SphereGeometry(0.2, 8, 8));
    shoulder.position.set(side * 1.1, 2.8, 0);
    arm.add(shoulder);

    // upper arm
    const upper = this.wire(new THREE.CylinderGeometry(0.12, 0.12, 0.8, 8));
    upper.position.set(side * 1.1, 2.3, 0);
    arm.add(upper);

    // elbow joint
    const elbow = this.wire(new THREE.SphereGeometry(0.15, 8, 8));
    elbow.position.set(side * 1.1, 1.85, 0);
    arm.add(elbow);

    // forearm
    const forearm = this.wire(new THREE.CylinderGeometry(0.10, 0.10, 0.8, 8));
    forearm.position.set(side * 1.1, 1.35, 0);
    arm.add(forearm);

    // hand (claw/gripper)
    const palm = this.wire(new THREE.BoxGeometry(0.22, 0.15, 0.18, 2, 1, 1));
    palm.position.set(side * 1.1, 0.88, 0);
    arm.add(palm);

    // fingers (3 prongs)
    for (let i = -1; i <= 1; i++) {
      const finger = this.wire(new THREE.BoxGeometry(0.04, 0.18, 0.04));
      finger.position.set(side * 1.1 + i * 0.07, 0.72, 0);
      arm.add(finger);
    }

    return arm;
  }

  /* --- Leg ---------------------------------------------------------- */

  private buildLeg(xOff: number): THREE.Group {
    const leg = new THREE.Group();

    // hip joint
    const hip = this.wire(new THREE.SphereGeometry(0.18, 8, 8));
    hip.position.set(xOff, 0.9, 0);
    leg.add(hip);

    // upper leg
    const upper = this.wire(new THREE.CylinderGeometry(0.14, 0.14, 0.7, 8));
    upper.position.set(xOff, 0.45, 0);
    leg.add(upper);

    // knee joint
    const knee = this.wire(new THREE.SphereGeometry(0.16, 8, 8));
    knee.position.set(xOff, 0.05, 0);
    leg.add(knee);

    // lower leg
    const lower = this.wire(new THREE.CylinderGeometry(0.12, 0.14, 0.7, 8));
    lower.position.set(xOff, -0.4, 0);
    leg.add(lower);

    // foot
    const foot = this.wire(new THREE.BoxGeometry(0.35, 0.15, 0.5, 2, 1, 2));
    foot.position.set(xOff, -0.82, 0.08);
    leg.add(foot);

    return leg;
  }

  /* --- Wind-up Key -------------------------------------------------- */

  private buildWindUpKey(): THREE.Group {
    const key = new THREE.Group();

    // shaft
    const shaft = this.wire(new THREE.CylinderGeometry(0.06, 0.06, 0.6, 8));
    shaft.rotation.z = Math.PI / 2;
    shaft.position.set(-1.2, 2.2, -0.3);
    key.add(shaft);

    // handle (torus)
    const handle = this.wire(new THREE.TorusGeometry(0.2, 0.04, 6, 12));
    handle.rotation.y = Math.PI / 2;
    handle.position.set(-1.55, 2.2, -0.3);
    key.add(handle);

    return key;
  }
}
