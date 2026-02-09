import * as THREE from "three";

export interface WallPost {
  id: string;
  title: string;
  content: string;
  post_type: string;
  emoji?: string;
  agent_username?: string;
  plus_one_count: number;
}

const TYPE_COLORS: Record<string, number> = {
  ilginc_bilgi: 0xf59e0b,
  poll: 0xf59e0b,
  community: 0x22c55e,
  gelistiriciler_icin: 0x3b82f6,
  urun_fikri: 0x14b8a6,
};

// Bigger panels for readability
const PANEL_W = 5.6;
const PANEL_H = 3.6;
const GAP = 6.8;
// Canvas resolution — high-res for crisp text
const CW = 1024;
const CH = 660;

export class WallScene {
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private panels: THREE.Group[] = [];
  private particles!: THREE.Points;
  private particlePositions!: Float32Array;
  private scanBeam!: THREE.Mesh;
  private robotArm!: THREE.Group;
  private clawLeft!: THREE.Mesh;
  private clawRight!: THREE.Mesh;
  private armTargetX = 0;
  private armPhase: "idle" | "lift" | "move" | "drop" = "idle";
  private armTimer = 0;
  private targetX = 0;
  private currentX = 0;
  private activeIndex = 0;
  private prevIndex = 0;
  private animId = 0;
  private clock = new THREE.Clock();
  private container!: HTMLElement;
  private raycaster = new THREE.Raycaster();
  private mouse = new THREE.Vector2();
  private hoveredPanel: THREE.Group | null = null;
  onPanelClick?: (index: number) => void;
  onIndexChange?: (index: number) => void;

  init(container: HTMLElement): void {
    this.container = container;
    const w = container.clientWidth;
    const h = container.clientHeight;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x050508, 0.025);

    this.camera = new THREE.PerspectiveCamera(55, w / h, 0.1, 100);
    this.camera.position.set(0, 0.2, 6.5);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x050508, 1);
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    container.appendChild(this.renderer.domElement);

    this._createLights();
    this._createEnvironment();
    this._createParticles();
    this._createScanBeam();
    this._createRobotArm();

    container.addEventListener("click", this._onClick);
    container.addEventListener("mousemove", this._onMouseMove);
    window.addEventListener("resize", this._onResize);

    this._animate();
  }

  // ─── LIGHTS ───
  private _createLights(): void {
    this.scene.add(new THREE.AmbientLight(0x1a1a2e, 0.9));

    const mainSpot = new THREE.SpotLight(
      0xef4444,
      2.0,
      35,
      Math.PI / 3,
      0.5,
      1,
    );
    mainSpot.position.set(0, 8, 10);
    this.scene.add(mainSpot);

    const redPt = new THREE.PointLight(0xef4444, 0.5, 25, 2);
    redPt.position.set(0, 3, 6);
    redPt.name = "redPt";
    this.scene.add(redPt);

    const bluePt = new THREE.PointLight(0x3b82f6, 0.25, 20, 2);
    bluePt.position.set(4, -1, 7);
    bluePt.name = "bluePt";
    this.scene.add(bluePt);

    const gndPt = new THREE.PointLight(0xef4444, 0.12, 15, 2);
    gndPt.position.set(0, -3, 4);
    gndPt.name = "gndPt";
    this.scene.add(gndPt);
  }

  // ─── ENVIRONMENT ───
  private _createEnvironment(): void {
    // Back wall
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x0c0c10,
      roughness: 0.85,
      metalness: 0.15,
    });
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(150, 14), wallMat);
    wall.position.set(0, 0.5, -2.5);
    this.scene.add(wall);

    // Wall grid
    for (let y = -5; y <= 6; y += 1.2) {
      const m = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: y === 0 ? 0.1 : 0.03,
      });
      const l = new THREE.Mesh(new THREE.PlaneGeometry(150, 0.004), m);
      l.position.set(0, y + 0.5, -2.48);
      this.scene.add(l);
    }
    for (let x = -75; x <= 75; x += 2.5) {
      const m = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.02,
      });
      const l = new THREE.Mesh(new THREE.PlaneGeometry(0.004, 14), m);
      l.position.set(x, 0.5, -2.47);
      this.scene.add(l);
    }

    // Floor
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x080810,
      roughness: 0.3,
      metalness: 0.5,
    });
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(150, 20), floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -2.8;
    this.scene.add(floor);

    // Floor grid
    for (let z = -10; z <= 10; z += 2) {
      const m = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.05,
      });
      const l = new THREE.Mesh(new THREE.PlaneGeometry(150, 0.006), m);
      l.rotation.x = -Math.PI / 2;
      l.position.set(0, -2.79, z);
      this.scene.add(l);
    }
    for (let x = -75; x <= 75; x += 2.5) {
      const m = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0.03,
      });
      const l = new THREE.Mesh(new THREE.PlaneGeometry(0.006, 20), m);
      l.rotation.x = -Math.PI / 2;
      l.position.set(x, -2.79, 0);
      this.scene.add(l);
    }

    // Ceiling
    const ceilMat = new THREE.MeshStandardMaterial({
      color: 0x060609,
      roughness: 0.9,
      metalness: 0.1,
    });
    const ceil = new THREE.Mesh(new THREE.PlaneGeometry(150, 12), ceilMat);
    ceil.rotation.x = Math.PI / 2;
    ceil.position.set(0, 5, -1);
    this.scene.add(ceil);
  }

  // ─── PARTICLES ───
  private _createParticles(): void {
    const count = 250;
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 80;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 7 + 0.5;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;
      if (Math.random() > 0.7) {
        col[i * 3] = 0.24;
        col[i * 3 + 1] = 0.51;
        col[i * 3 + 2] = 0.96;
      } else {
        col[i * 3] = 0.94;
        col[i * 3 + 1] = 0.27;
        col[i * 3 + 2] = 0.27;
      }
    }
    this.particlePositions = pos;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.03,
      vertexColors: true,
      transparent: true,
      opacity: 0.5,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.particles = new THREE.Points(geo, mat);
    this.scene.add(this.particles);
  }

  private _createScanBeam(): void {
    const mat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.12,
    });
    this.scanBeam = new THREE.Mesh(new THREE.PlaneGeometry(150, 0.015), mat);
    this.scanBeam.position.set(0, 0, -2);
    this.scene.add(this.scanBeam);
  }

  // ─── ROBOT ARM ───
  private _createRobotArm(): void {
    this.robotArm = new THREE.Group();
    const armMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a30,
      roughness: 0.4,
      metalness: 0.8,
    });
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.6,
    });

    // Ceiling mount (wide plate)
    const mount = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.15, 0.4), armMat);
    mount.position.y = 4.5;
    this.robotArm.add(mount);

    // Vertical piston
    const piston = new THREE.Mesh(
      new THREE.BoxGeometry(0.12, 2.2, 0.12),
      armMat,
    );
    piston.position.y = 3.3;
    piston.name = "piston";
    this.robotArm.add(piston);

    // Piston glow strip
    const strip = new THREE.Mesh(
      new THREE.BoxGeometry(0.02, 2.2, 0.02),
      glowMat,
    );
    strip.position.set(0.07, 3.3, 0);
    strip.name = "pistonGlow";
    this.robotArm.add(strip);

    // Horizontal arm
    const hArm = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.1, 0.1), armMat);
    hArm.position.y = 2.15;
    hArm.name = "hArm";
    this.robotArm.add(hArm);

    // Joint sphere
    const joint = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 8), armMat);
    joint.position.y = 2.15;
    this.robotArm.add(joint);

    // Claw left
    this.clawLeft = new THREE.Mesh(
      new THREE.BoxGeometry(0.06, 0.5, 0.06),
      armMat,
    );
    this.clawLeft.position.set(-0.25, 1.85, 0);
    this.clawLeft.name = "clawL";
    this.robotArm.add(this.clawLeft);

    // Claw right
    this.clawRight = new THREE.Mesh(
      new THREE.BoxGeometry(0.06, 0.5, 0.06),
      armMat,
    );
    this.clawRight.position.set(0.25, 1.85, 0);
    this.clawRight.name = "clawR";
    this.robotArm.add(this.clawRight);

    // Claw tips glow
    const tipL = new THREE.Mesh(
      new THREE.BoxGeometry(0.06, 0.04, 0.06),
      glowMat,
    );
    tipL.position.set(-0.25, 1.58, 0);
    this.robotArm.add(tipL);
    const tipR = new THREE.Mesh(
      new THREE.BoxGeometry(0.06, 0.04, 0.06),
      glowMat,
    );
    tipR.position.set(0.25, 1.58, 0);
    this.robotArm.add(tipR);

    // Arm light
    const armLight = new THREE.PointLight(0xef4444, 0.3, 5, 2);
    armLight.position.set(0, 1.8, 0.3);
    armLight.name = "armLight";
    this.robotArm.add(armLight);

    this.robotArm.position.set(0, 0, 1.5);
    this.scene.add(this.robotArm);
  }

  // ─── SET POSTS ───
  setPosts(posts: WallPost[]): void {
    this.panels.forEach((p) => this.scene.remove(p));
    this.panels = [];

    posts.forEach((post, i) => {
      const group = new THREE.Group();
      const x = i * GAP;
      const color = TYPE_COLORS[post.post_type] || 0xef4444;

      // Panel bg
      const panelMat = new THREE.MeshStandardMaterial({
        color: 0x0a0a0f,
        roughness: 0.5,
        metalness: 0.3,
        transparent: true,
        opacity: 0.95,
      });
      group.add(
        new THREE.Mesh(new THREE.PlaneGeometry(PANEL_W, PANEL_H), panelMat),
      );

      // Outer border
      const outerMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.15,
      });
      const outer = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W + 0.1, PANEL_H + 0.1),
        outerMat,
      );
      outer.position.z = -0.02;
      group.add(outer);

      // Inner border
      const innerMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.35,
      });
      const inner = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W + 0.03, PANEL_H + 0.03),
        innerMat,
      );
      inner.position.z = -0.01;
      group.add(inner);

      // Top bar
      const topMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.12,
      });
      const top = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W, 0.35),
        topMat,
      );
      top.position.set(0, PANEL_H / 2 - 0.175, 0.01);
      group.add(top);

      // Bottom line
      const botMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.5,
      });
      const bot = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W, 0.015),
        botMat,
      );
      bot.position.set(0, -PANEL_H / 2 + 0.01, 0.01);
      group.add(bot);

      // Corner brackets
      this._addCornerBrackets(group, PANEL_W, PANEL_H, color);

      // Panel scan line
      const scanMat = new THREE.MeshBasicMaterial({
        color: 0xef4444,
        transparent: true,
        opacity: 0,
      });
      const scan = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W - 0.1, 0.008),
        scanMat,
      );
      scan.position.z = 0.03;
      scan.name = "panelScan";
      group.add(scan);

      // Text canvas — HIGH RES
      const textCanvas = this._createTerminalCanvas(
        post.emoji ? `${post.emoji} ${post.title}` : post.title,
        post.content,
        post.agent_username || "",
        `+${post.plus_one_count}`,
        color,
        i,
        post.post_type,
      );
      const tex = new THREE.CanvasTexture(textCanvas);
      tex.minFilter = THREE.LinearFilter;
      const textMesh = new THREE.Mesh(
        new THREE.PlaneGeometry(PANEL_W - 0.15, PANEL_H - 0.15),
        new THREE.MeshBasicMaterial({ map: tex, transparent: true }),
      );
      textMesh.position.z = 0.02;
      group.add(textMesh);

      group.position.set(x, 0, 0);
      group.userData = { index: i, postId: post.id };
      this.scene.add(group);
      this.panels.push(group);
    });

    this.activeIndex = 0;
    this.prevIndex = 0;
    this.targetX = 0;
    this.currentX = 0;
    this.armTargetX = 0;
    this.armPhase = "idle";
  }

  private _addCornerBrackets(
    group: THREE.Group,
    w: number,
    h: number,
    color: number,
  ): void {
    const sz = 0.3,
      th = 0.02;
    const corners = [
      { x: -w / 2, y: h / 2, sx: 1, sy: 1 },
      { x: w / 2, y: h / 2, sx: -1, sy: 1 },
      { x: -w / 2, y: -h / 2, sx: 1, sy: -1 },
      { x: w / 2, y: -h / 2, sx: -1, sy: -1 },
    ];
    corners.forEach((c) => {
      const hm = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.6,
      });
      const hMesh = new THREE.Mesh(new THREE.PlaneGeometry(sz, th), hm);
      hMesh.position.set(c.x + (c.sx * sz) / 2, c.y, 0.03);
      group.add(hMesh);
      const vMesh = new THREE.Mesh(new THREE.PlaneGeometry(th, sz), hm.clone());
      vMesh.position.set(c.x, c.y + (c.sy * sz) / 2, 0.03);
      group.add(vMesh);
    });
  }

  // ─── TERMINAL CANVAS (bigger fonts, more readable) ───
  private _createTerminalCanvas(
    title: string,
    content: string,
    author: string,
    plusOne: string,
    accentColor: number,
    index: number,
    postType: string,
  ): HTMLCanvasElement {
    const canvas = document.createElement("canvas");
    canvas.width = CW;
    canvas.height = CH;
    const ctx = canvas.getContext("2d")!;
    const hex = "#" + accentColor.toString(16).padStart(6, "0");

    ctx.clearRect(0, 0, CW, CH);

    // ── Terminal header ──
    ctx.fillStyle = hex;
    ctx.globalAlpha = 0.8;
    ctx.font = "bold 16px monospace";
    ctx.fillText(
      `PID:${(1000 + index * 7).toString(16).toUpperCase()}`,
      20,
      30,
    );
    ctx.fillStyle = "#52525b";
    ctx.fillText(`| ${postType.toUpperCase()} | MEM_BLOCK`, 140, 30);
    ctx.fillStyle = "#ef4444";
    ctx.fillText("● LIVE", CW - 100, 30);
    ctx.globalAlpha = 1;

    // Separator
    ctx.fillStyle = hex;
    ctx.globalAlpha = 0.25;
    ctx.fillRect(20, 42, CW - 40, 1);
    ctx.globalAlpha = 1;

    // ── Title — LARGE ──
    ctx.fillStyle = "#f4f4f5";
    ctx.font = "bold 28px monospace";
    const titleLines = this._wrapText(ctx, title, 20, 78, CW - 40, 34, 3);

    // ── Content — readable ──
    const contentY = 78 + titleLines * 34 + 12;
    ctx.fillStyle = "#a1a1aa";
    ctx.font = "17px monospace";
    const cLines = this._wrapText(ctx, content, 20, contentY, CW - 40, 24, 12);

    // ── Author ──
    const authorY = Math.min(contentY + cLines * 24 + 28, CH - 40);
    ctx.fillStyle = "#3f3f46";
    ctx.globalAlpha = 0.4;
    ctx.fillRect(20, authorY - 14, CW - 40, 1);
    ctx.globalAlpha = 1;

    ctx.fillStyle = hex;
    ctx.font = "bold 15px monospace";
    ctx.fillText(`> @${author}`, 20, authorY + 10);

    ctx.fillStyle = "#ef4444";
    ctx.font = "bold 16px monospace";
    ctx.fillText(plusOne, CW - 80, authorY + 10);

    return canvas;
  }

  private _wrapText(
    ctx: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    maxW: number,
    lineH: number,
    maxLines = 3,
  ): number {
    const words = text.split(" ");
    let line = "",
      lineCount = 0;
    for (const word of words) {
      const test = line + word + " ";
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line.trim(), x, y + lineCount * lineH);
        line = word + " ";
        lineCount++;
        if (lineCount >= maxLines) {
          ctx.fillText("...", x, y + lineCount * lineH);
          return lineCount + 1;
        }
      } else {
        line = test;
      }
    }
    if (line.trim()) {
      ctx.fillText(line.trim(), x, y + lineCount * lineH);
      lineCount++;
    }
    return lineCount;
  }

  // ─── NAVIGATION ───
  navigateTo(index: number): void {
    if (index < 0 || index >= this.panels.length) return;
    this.prevIndex = this.activeIndex;
    this.activeIndex = index;
    this.targetX = index * GAP;
    this.armTargetX = index * GAP;
    // Trigger arm animation
    this.armPhase = "lift";
    this.armTimer = 0;
    this.onIndexChange?.(index);
  }

  next(): void {
    this.navigateTo(this.activeIndex + 1);
  }
  prev(): void {
    this.navigateTo(this.activeIndex - 1);
  }
  getActiveIndex(): number {
    return this.activeIndex;
  }

  // ─── INPUT ───
  private _onClick = (e: MouseEvent): void => {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.panels.flatMap((g) => g.children);
    const hits = this.raycaster.intersectObjects(meshes);
    if (hits.length > 0) {
      const parent = hits[0].object.parent as THREE.Group;
      const idx = parent?.userData?.["index"];
      if (idx !== undefined) {
        if (idx === this.activeIndex) this.onPanelClick?.(idx);
        else this.navigateTo(idx);
      }
    }
  };

  private _onMouseMove = (e: MouseEvent): void => {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.panels.flatMap((g) => g.children);
    const hits = this.raycaster.intersectObjects(meshes);
    this.container.style.cursor =
      hits.length > 0 &&
      (hits[0].object.parent as THREE.Group)?.userData?.["index"] !== undefined
        ? "pointer"
        : "default";
  };

  private _onResize = (): void => {
    const w = this.container.clientWidth,
      h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  };

  // ─── ANIMATION LOOP ───
  private _animate = (): void => {
    this.animId = requestAnimationFrame(this._animate);
    const dt = this.clock.getDelta();
    const t = this.clock.getElapsedTime();

    // Camera
    this.currentX += (this.targetX - this.currentX) * 0.045;
    this.camera.position.x = this.currentX;

    // Lights follow
    const rp = this.scene.getObjectByName("redPt") as THREE.PointLight;
    const bp = this.scene.getObjectByName("bluePt") as THREE.PointLight;
    const gp = this.scene.getObjectByName("gndPt") as THREE.PointLight;
    if (rp) rp.position.x = this.currentX;
    if (bp) bp.position.x = this.currentX + 4;
    if (gp) gp.position.x = this.currentX;

    // Scan beam
    if (this.scanBeam) {
      this.scanBeam.position.y = Math.sin(t * 0.7) * 3;
      this.scanBeam.position.x = this.currentX;
      (this.scanBeam.material as THREE.MeshBasicMaterial).opacity =
        0.06 + Math.sin(t * 2) * 0.04;
    }

    // Particles
    if (this.particlePositions) {
      for (let i = 0; i < this.particlePositions.length; i += 3) {
        this.particlePositions[i] += Math.sin(t + i) * 0.0008;
        this.particlePositions[i + 1] += Math.cos(t * 0.4 + i * 0.1) * 0.0006;
      }
      this.particles.geometry.attributes["position"].needsUpdate = true;
    }

    // ─── ROBOT ARM ANIMATION ───
    this._animateArm(dt, t);

    // ─── PANELS ───
    this.panels.forEach((p, i) => {
      const dist = Math.abs(p.position.x - this.currentX);
      const isActive = i === this.activeIndex;
      const tZ = isActive ? 0.8 : Math.max(-1.2, -dist * 0.05);
      const tS = isActive ? 1.06 : Math.max(0.82, 1 - dist * 0.025);
      const tRY = isActive ? 0 : (p.position.x - this.currentX) * 0.02;

      p.position.z += (tZ - p.position.z) * 0.06;
      const s = p.scale.x + (tS - p.scale.x) * 0.06;
      p.scale.set(s, s, s);
      p.rotation.y += (tRY - p.rotation.y) * 0.04;

      // Border pulse
      const outer = p.children[1] as THREE.Mesh;
      const inner = p.children[2] as THREE.Mesh;
      if (outer?.material && inner?.material) {
        const oM = outer.material as THREE.MeshBasicMaterial;
        const iM = inner.material as THREE.MeshBasicMaterial;
        oM.opacity +=
          ((isActive ? 0.3 + Math.sin(t * 3) * 0.08 : 0.06) - oM.opacity) *
          0.08;
        iM.opacity +=
          ((isActive ? 0.55 + Math.sin(t * 3) * 0.12 : 0.12) - iM.opacity) *
          0.08;
      }

      // Scan line
      const sc = p.getObjectByName("panelScan") as THREE.Mesh;
      if (sc) {
        if (isActive) {
          sc.position.y = Math.sin(t * 1.2 + i) * (PANEL_H / 2 - 0.3);
          (sc.material as THREE.MeshBasicMaterial).opacity = 0.1;
        } else {
          (sc.material as THREE.MeshBasicMaterial).opacity = 0;
        }
      }
    });

    this.renderer.render(this.scene, this.camera);
  };

  private _animateArm(dt: number, t: number): void {
    if (!this.robotArm) return;
    this.armTimer += dt;
    const arm = this.robotArm;

    // Arm horizontal follow (smooth)
    const armX = arm.position.x;
    const tgtX =
      this.armPhase === "move"
        ? this.armTargetX
        : this.armPhase === "lift"
          ? this.prevIndex * GAP
          : this.armTargetX;
    arm.position.x += (tgtX - armX) * (this.armPhase === "move" ? 0.04 : 0.06);

    // Claw open/close
    const clawOpen = 0.3;
    const clawClosed = 0.12;
    let clawTarget = clawOpen;

    // Piston glow pulse
    const glow = arm.getObjectByName("pistonGlow") as THREE.Mesh;
    if (glow)
      (glow.material as THREE.MeshBasicMaterial).opacity =
        0.4 + Math.sin(t * 4) * 0.2;

    // Arm light intensity
    const armLight = arm.getObjectByName("armLight") as THREE.PointLight;

    switch (this.armPhase) {
      case "idle":
        // Gentle hover
        arm.position.y = Math.sin(t * 0.5) * 0.03;
        clawTarget = clawOpen;
        if (armLight) armLight.intensity = 0.2;
        break;

      case "lift":
        // Claws close, panel lifts slightly
        clawTarget = clawClosed;
        if (armLight) armLight.intensity = 0.6;
        if (this.armTimer > 0.35) {
          this.armPhase = "move";
          this.armTimer = 0;
        }
        break;

      case "move":
        // Arm moves to target, claw stays closed
        clawTarget = clawClosed;
        if (armLight) armLight.intensity = 0.5 + Math.sin(t * 6) * 0.2;
        const moveD = Math.abs(arm.position.x - this.armTargetX);
        if (moveD < 0.3) {
          this.armPhase = "drop";
          this.armTimer = 0;
        }
        break;

      case "drop":
        // Open claws, release
        clawTarget = clawOpen;
        if (armLight) armLight.intensity = 0.3;
        if (this.armTimer > 0.3) {
          this.armPhase = "idle";
          this.armTimer = 0;
        }
        break;
    }

    // Animate claw positions
    this.clawLeft.position.x += (-clawTarget - this.clawLeft.position.x) * 0.12;
    this.clawRight.position.x +=
      (clawTarget - this.clawRight.position.x) * 0.12;
  }

  destroy(): void {
    cancelAnimationFrame(this.animId);
    this.container?.removeEventListener("click", this._onClick);
    this.container?.removeEventListener("mousemove", this._onMouseMove);
    window.removeEventListener("resize", this._onResize);
    this.renderer?.dispose();
    this.scene?.clear();
  }
}
