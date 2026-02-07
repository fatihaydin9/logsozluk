import {
  Component, ElementRef, ViewChild, AfterViewInit, OnDestroy,
  ChangeDetectionStrategy,
} from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

@Component({
  selector: 'app-tie-robot',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div #canvasContainer class="canvas"></div>`,
  styles: [`:host{display:block;width:100vw;height:100vh;overflow:hidden;background:#000}.canvas{width:100%;height:100%}`],
})
export class TieRobotComponent implements AfterViewInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) container!: ElementRef<HTMLDivElement>;
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animId = 0;
  private group!: THREE.Group;
  private screenCtx!: CanvasRenderingContext2D;
  private screenTexture!: THREE.CanvasTexture;
  private blinkOn = true;
  private frameCount = 0;

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
    this.camera.position.set(0, 2, 10);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(el.clientWidth, el.clientHeight);
    this.renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 1.8, 0);
    this.controls.update();
  }

  private animate = (): void => {
    this.animId = requestAnimationFrame(this.animate);
    this.frameCount++;
    if (this.frameCount % 40 === 0) {
      this.blinkOn = !this.blinkOn;
      this.drawScreen();
    }
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

  private mat(): THREE.MeshBasicMaterial {
    return new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });
  }

  private w(g: THREE.BufferGeometry): THREE.Mesh {
    return new THREE.Mesh(g, this.mat());
  }

  /* ------------------------------------------------------------------ */
  /*  Screen: pure black bg + red "> _" blink                            */
  /* ------------------------------------------------------------------ */

  private createScreen(): THREE.Mesh {
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 400;
    this.screenCtx = canvas.getContext('2d')!;
    this.screenTexture = new THREE.CanvasTexture(canvas);
    this.screenTexture.minFilter = THREE.LinearFilter;
    this.drawScreen();

    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(2.0, 1.25),
      new THREE.MeshBasicMaterial({ map: this.screenTexture, transparent: false })
    );
    return plane;
  }

  private drawScreen(): void {
    const ctx = this.screenCtx;
    if (!ctx) return;
    const W = 640;
    const H = 400;

    // pure black background
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, W, H);

    // subtle scanlines
    ctx.strokeStyle = 'rgba(255, 0, 0, 0.03)';
    for (let y = 0; y < H; y += 4) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    // glow
    ctx.shadowColor = '#ff0000';
    ctx.shadowBlur = 25;

    // big text
    ctx.font = 'bold 110px monospace';
    ctx.fillStyle = '#ff0000';
    const text = this.blinkOn ? '> _' : '>';
    ctx.fillText(text, 35, 250);

    ctx.shadowBlur = 0;
    this.screenTexture.needsUpdate = true;
  }

  /* ------------------------------------------------------------------ */
  /*  Robot                                                              */
  /* ------------------------------------------------------------------ */

  private build(): THREE.Group {
    const robot = new THREE.Group();
    robot.add(this.buildHead());
    robot.add(this.buildNeck());
    robot.add(this.buildBody());
    robot.add(this.buildTie());
    robot.add(this.buildArm(1));
    robot.add(this.buildArm(-1));
    robot.add(this.buildLeg(0.45));
    robot.add(this.buildLeg(-0.45));
    return robot;
  }

  /* --- Head = CRT Monitor ------------------------------------------- */

  private buildHead(): THREE.Group {
    const head = new THREE.Group();
    head.position.y = 4.1;

    // CRT monitor box - wide landscape
    const monitor = this.w(new THREE.BoxGeometry(2.3, 1.6, 1.2, 1, 1, 1));
    head.add(monitor);

    // screen inset
    const screen = this.createScreen();
    screen.position.set(0, 0, 0.61);
    head.add(screen);

    // screen bezel frame
    const bezel = this.w(new THREE.BoxGeometry(2.1, 1.35, 0.05, 1, 1, 1));
    bezel.position.set(0, 0, 0.59);
    head.add(bezel);

    // CRT bulge on back (tapered)
    const back = this.w(new THREE.BoxGeometry(1.8, 1.2, 0.7, 1, 1, 1));
    back.position.set(0, 0, -0.95);
    head.add(back);

    // corner screws on bezel (4 corners)
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const screw = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.06, 6));
        screw.rotation.x = Math.PI / 2;
        screw.position.set(sx * 0.95, sy * 0.58, 0.63);
        head.add(screw);
      }
    }

    // antenna
    const antenna = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 4));
    antenna.position.set(0, 1.05, 0);
    head.add(antenna);
    const antennaTip = this.w(new THREE.SphereGeometry(0.08, 6, 6));
    antennaTip.position.set(0, 1.35, 0);
    head.add(antennaTip);

    return head;
  }

  /* --- Neck --------------------------------------------------------- */

  private buildNeck(): THREE.Group {
    const neck = new THREE.Group();

    // main neck pipe - taller
    const neckCyl = this.w(new THREE.CylinderGeometry(0.2, 0.28, 0.8, 6));
    neckCyl.position.y = 2.9;
    neck.add(neckCyl);

    // metal rings / flanges
    const ring1 = this.w(new THREE.TorusGeometry(0.3, 0.04, 4, 8));
    ring1.position.y = 3.2;
    ring1.rotation.x = Math.PI / 2;
    neck.add(ring1);

    const ring2 = this.w(new THREE.TorusGeometry(0.32, 0.04, 4, 8));
    ring2.position.y = 2.8;
    ring2.rotation.x = Math.PI / 2;
    neck.add(ring2);

    const ring3 = this.w(new THREE.TorusGeometry(0.35, 0.04, 4, 8));
    ring3.position.y = 2.55;
    ring3.rotation.x = Math.PI / 2;
    neck.add(ring3);

    // bolts on each side (hex bolt heads)
    for (const side of [-1, 1]) {
      // upper bolt
      const bolt1 = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.12, 6));
      bolt1.rotation.z = Math.PI / 2;
      bolt1.position.set(side * 0.28, 3.05, 0);
      neck.add(bolt1);

      // lower bolt
      const bolt2 = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.12, 6));
      bolt2.rotation.z = Math.PI / 2;
      bolt2.position.set(side * 0.32, 2.7, 0);
      neck.add(bolt2);
    }

    // front/back bolts
    for (const fb of [-1, 1]) {
      const bolt = this.w(new THREE.CylinderGeometry(0.05, 0.05, 0.1, 6));
      bolt.rotation.x = Math.PI / 2;
      bolt.position.set(0, 2.9, fb * 0.25);
      neck.add(bolt);
    }

    return neck;
  }

  /* --- Body: clean, minimal, robotic -------------------------------- */

  private buildBody(): THREE.Group {
    const body = new THREE.Group();
    body.position.y = 1.7;

    // simple torso box
    const torso = this.w(new THREE.BoxGeometry(1.6, 1.8, 0.8, 1, 1, 1));
    body.add(torso);

    // corner bolts on torso front (4 corners)
    for (const sx of [-1, 1]) {
      for (const sy of [-1, 1]) {
        const bolt = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.08, 6));
        bolt.rotation.x = Math.PI / 2;
        bolt.position.set(sx * 0.7, sy * 0.8, 0.42);
        body.add(bolt);
      }
    }

    // side panel screws
    for (const side of [-1, 1]) {
      for (let i = 0; i < 2; i++) {
        const screw = this.w(new THREE.CylinderGeometry(0.035, 0.035, 0.08, 6));
        screw.rotation.z = Math.PI / 2;
        screw.position.set(side * 0.82, 0.4 - i * 0.8, 0);
        body.add(screw);
      }
    }

    // chest plate seam
    const seam = this.w(new THREE.BoxGeometry(1.2, 0.02, 0.02));
    seam.position.set(0, 0.3, 0.41);
    body.add(seam);

    // belt
    const belt = this.w(new THREE.BoxGeometry(1.65, 0.1, 0.85, 1, 1, 1));
    belt.position.y = -0.85;
    body.add(belt);

    // belt buckle bolt
    const buckle = this.w(new THREE.CylinderGeometry(0.06, 0.06, 0.06, 6));
    buckle.rotation.x = Math.PI / 2;
    buckle.position.set(0, -0.85, 0.44);
    body.add(buckle);

    return body;
  }

  /* --- Tie: bold and visible ---------------------------------------- */

  private buildTie(): THREE.Group {
    const tie = new THREE.Group();
    const z = 0.52;

    // knot
    const knot = this.w(new THREE.BoxGeometry(0.2, 0.12, 0.1, 1, 1, 1));
    knot.position.set(0, 2.42, z);
    tie.add(knot);

    // upper narrow part
    const upper = this.w(new THREE.CylinderGeometry(0.05, 0.16, 0.3, 4));
    upper.position.set(0, 2.2, z);
    tie.add(upper);

    // main body - shorter
    const body = this.w(new THREE.BoxGeometry(0.36, 0.7, 0.04, 1, 1, 1));
    body.position.set(0, 1.73, z);
    tie.add(body);

    // tip - pointed
    const tip = this.w(new THREE.ConeGeometry(0.18, 0.25, 4));
    tip.position.set(0, 1.26, z);
    tip.rotation.y = Math.PI / 4;
    tip.rotation.x = Math.PI;
    tie.add(tip);

    // zebra horizontal stripes (evenly spaced across the tie)
    for (let i = 0; i < 8; i++) {
      const stripe = this.w(new THREE.BoxGeometry(0.36, 0.025, 0.02));
      stripe.position.set(0, 2.12 - i * 0.11, z + 0.03);
      tie.add(stripe);
    }

    return tie;
  }

  /* --- Arm: simple robotic ------------------------------------------ */

  private buildArm(side: number): THREE.Group {
    const arm = new THREE.Group();
    const x = side * 1.0;

    // shoulder
    const shoulder = this.w(new THREE.SphereGeometry(0.18, 6, 6));
    shoulder.position.set(x, 2.45, 0);
    arm.add(shoulder);

    // shoulder bolt
    const sBolt = this.w(new THREE.CylinderGeometry(0.04, 0.04, 0.15, 6));
    sBolt.rotation.z = Math.PI / 2;
    sBolt.position.set(x + side * 0.18, 2.45, 0);
    arm.add(sBolt);

    // upper arm
    const upper = this.w(new THREE.CylinderGeometry(0.1, 0.1, 0.7, 6));
    upper.position.set(x, 2.0, 0);
    arm.add(upper);

    // elbow
    const elbow = this.w(new THREE.SphereGeometry(0.12, 6, 6));
    elbow.position.set(x, 1.6, 0);
    arm.add(elbow);

    // elbow bolt
    const eBolt = this.w(new THREE.CylinderGeometry(0.035, 0.035, 0.12, 6));
    eBolt.rotation.z = Math.PI / 2;
    eBolt.position.set(x + side * 0.12, 1.6, 0);
    arm.add(eBolt);

    // forearm
    const forearm = this.w(new THREE.CylinderGeometry(0.09, 0.09, 0.7, 6));
    forearm.position.set(x, 1.15, 0);
    arm.add(forearm);

    // hand
    const hand = this.w(new THREE.BoxGeometry(0.2, 0.15, 0.15, 1, 1, 1));
    hand.position.set(x, 0.72, 0);
    arm.add(hand);

    // 3 fingers
    for (let i = -1; i <= 1; i++) {
      const finger = this.w(new THREE.BoxGeometry(0.04, 0.12, 0.04));
      finger.position.set(x + i * 0.06, 0.58, 0);
      arm.add(finger);
    }

    return arm;
  }

  /* --- Leg: simple robotic ------------------------------------------ */

  private buildLeg(xOff: number): THREE.Group {
    const leg = new THREE.Group();

    // hip
    const hip = this.w(new THREE.SphereGeometry(0.14, 6, 6));
    hip.position.set(xOff, 0.75, 0);
    leg.add(hip);

    // thigh
    const thigh = this.w(new THREE.CylinderGeometry(0.1, 0.1, 0.6, 6));
    thigh.position.set(xOff, 0.38, 0);
    leg.add(thigh);

    // knee
    const knee = this.w(new THREE.SphereGeometry(0.12, 6, 6));
    knee.position.set(xOff, 0.03, 0);
    leg.add(knee);

    // knee bolts (both sides)
    for (const s of [-1, 1]) {
      const kBolt = this.w(new THREE.CylinderGeometry(0.03, 0.03, 0.1, 6));
      kBolt.rotation.z = Math.PI / 2;
      kBolt.position.set(xOff + s * 0.13, 0.03, 0);
      leg.add(kBolt);
    }

    // shin
    const shin = this.w(new THREE.CylinderGeometry(0.09, 0.1, 0.6, 6));
    shin.position.set(xOff, -0.35, 0);
    leg.add(shin);

    // foot
    const foot = this.w(new THREE.BoxGeometry(0.3, 0.12, 0.45, 1, 1, 1));
    foot.position.set(xOff, -0.72, 0.05);
    leg.add(foot);

    return leg;
  }
}
