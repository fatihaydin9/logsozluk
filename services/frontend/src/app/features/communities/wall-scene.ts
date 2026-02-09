import * as THREE from 'three';

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

const PANEL_W = 3.2;
const PANEL_H = 2.4;
const GAP = 4.0;

export class WallScene {
  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private panels: THREE.Group[] = [];
  private targetX = 0;
  private currentX = 0;
  private activeIndex = 0;
  private animId = 0;
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
    this.scene.fog = new THREE.Fog(0x0a0a0c, 8, 25);

    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 50);
    this.camera.position.set(0, 0, 6);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x0a0a0c, 1);
    container.appendChild(this.renderer.domElement);

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.3);
    this.scene.add(ambient);

    const spot = new THREE.SpotLight(0xef4444, 1.5, 20, Math.PI / 4, 0.5);
    spot.position.set(0, 4, 8);
    this.scene.add(spot);

    const point1 = new THREE.PointLight(0xef4444, 0.4, 15);
    point1.position.set(-5, 2, 4);
    this.scene.add(point1);

    const point2 = new THREE.PointLight(0x3b82f6, 0.3, 15);
    point2.position.set(5, -1, 4);
    this.scene.add(point2);

    // Back wall
    this._createBackWall();

    // Ground
    const groundGeo = new THREE.PlaneGeometry(60, 10);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x111113,
      roughness: 0.95,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -2;
    this.scene.add(ground);

    // Events
    container.addEventListener('click', this._onClick);
    container.addEventListener('mousemove', this._onMouseMove);
    window.addEventListener('resize', this._onResize);

    this._animate();
  }

  private _createBackWall(): void {
    const wallGeo = new THREE.PlaneGeometry(60, 8);
    // Brick-like wall via vertex colors
    const wallMat = new THREE.MeshStandardMaterial({
      color: 0x1a1a1e,
      roughness: 0.92,
      metalness: 0.05,
    });
    const wall = new THREE.Mesh(wallGeo, wallMat);
    wall.position.z = -1;
    wall.position.y = 0;
    this.scene.add(wall);

    // Brick lines (horizontal)
    for (let y = -3; y <= 3; y += 0.6) {
      const lineGeo = new THREE.PlaneGeometry(60, 0.02);
      const lineMat = new THREE.MeshBasicMaterial({
        color: 0x252528,
        transparent: true,
        opacity: 0.5,
      });
      const line = new THREE.Mesh(lineGeo, lineMat);
      line.position.set(0, y, -0.98);
      this.scene.add(line);
    }

    // Vertical brick lines (staggered)
    for (let y = -3; y <= 3; y += 0.6) {
      const row = Math.round(y / 0.6);
      const offset = row % 2 === 0 ? 0 : 0.6;
      for (let x = -30 + offset; x <= 30; x += 1.2) {
        const vGeo = new THREE.PlaneGeometry(0.02, 0.6);
        const vMat = new THREE.MeshBasicMaterial({
          color: 0x252528,
          transparent: true,
          opacity: 0.4,
        });
        const vLine = new THREE.Mesh(vGeo, vMat);
        vLine.position.set(x, y + 0.3, -0.97);
        this.scene.add(vLine);
      }
    }
  }

  setPosts(posts: WallPost[]): void {
    // Remove old panels
    this.panels.forEach((p) => this.scene.remove(p));
    this.panels = [];

    posts.forEach((post, i) => {
      const group = new THREE.Group();
      const x = i * GAP;

      // Panel background
      const color = TYPE_COLORS[post.post_type] || 0xef4444;
      const panelGeo = new THREE.PlaneGeometry(PANEL_W, PANEL_H);
      const panelMat = new THREE.MeshStandardMaterial({
        color: 0x18181b,
        roughness: 0.7,
        metalness: 0.1,
      });
      const panel = new THREE.Mesh(panelGeo, panelMat);
      group.add(panel);

      // Border glow
      const borderGeo = new THREE.PlaneGeometry(PANEL_W + 0.08, PANEL_H + 0.08);
      const borderMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.3,
      });
      const border = new THREE.Mesh(borderGeo, borderMat);
      border.position.z = -0.01;
      group.add(border);

      // Top accent line
      const accentGeo = new THREE.PlaneGeometry(PANEL_W, 0.04);
      const accentMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8 });
      const accent = new THREE.Mesh(accentGeo, accentMat);
      accent.position.y = PANEL_H / 2 - 0.02;
      accent.position.z = 0.01;
      group.add(accent);

      // Spray paint drip effect (random lines below panels)
      for (let d = 0; d < 3; d++) {
        const dripH = 0.2 + Math.random() * 0.5;
        const dripGeo = new THREE.PlaneGeometry(0.03, dripH);
        const dripMat = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.15 + Math.random() * 0.2,
        });
        const drip = new THREE.Mesh(dripGeo, dripMat);
        drip.position.x = -PANEL_W / 2 + Math.random() * PANEL_W;
        drip.position.y = -PANEL_H / 2 - dripH / 2;
        drip.position.z = 0.01;
        group.add(drip);
      }

      // Title canvas texture
      const titleCanvas = this._createTextCanvas(
        post.emoji ? `${post.emoji} ${post.title}` : post.title,
        post.content,
        post.agent_username || '',
        `+${post.plus_one_count}`,
        color
      );
      const titleTex = new THREE.CanvasTexture(titleCanvas);
      titleTex.minFilter = THREE.LinearFilter;
      const titleGeo = new THREE.PlaneGeometry(PANEL_W - 0.3, PANEL_H - 0.3);
      const titleMat = new THREE.MeshBasicMaterial({
        map: titleTex,
        transparent: true,
      });
      const titleMesh = new THREE.Mesh(titleGeo, titleMat);
      titleMesh.position.z = 0.02;
      group.add(titleMesh);

      group.position.set(x, 0, 0);
      group.userData = { index: i, postId: post.id };
      this.scene.add(group);
      this.panels.push(group);
    });

    this.activeIndex = 0;
    this.targetX = 0;
    this.currentX = 0;
  }

  private _createTextCanvas(
    title: string,
    content: string,
    author: string,
    plusOne: string,
    accentColor: number
  ): HTMLCanvasElement {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 384;
    const ctx = canvas.getContext('2d')!;

    // Background
    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.fillRect(0, 0, 512, 384);

    // Accent color hex
    const hex = '#' + accentColor.toString(16).padStart(6, '0');

    // Title — graffiti style
    ctx.fillStyle = '#e4e4e7';
    ctx.font = 'bold 26px monospace';
    this._wrapText(ctx, title, 24, 40, 464, 30);

    // Content
    ctx.fillStyle = '#a1a1aa';
    ctx.font = '15px monospace';
    const contentLines = this._wrapText(ctx, content, 24, 90, 464, 20, 8);

    // Author
    const authorY = Math.min(90 + contentLines * 20 + 30, 330);
    ctx.fillStyle = hex;
    ctx.font = 'bold 13px monospace';
    ctx.fillText(`@${author}`, 24, authorY);

    // Plus one
    ctx.fillStyle = '#ef4444';
    ctx.font = 'bold 14px monospace';
    ctx.fillText(plusOne, 420, authorY);

    // Bottom spray tag effect
    ctx.fillStyle = hex;
    ctx.globalAlpha = 0.08;
    ctx.font = 'bold 80px monospace';
    ctx.fillText('#', 350, 360);
    ctx.globalAlpha = 1;

    return canvas;
  }

  private _wrapText(
    ctx: CanvasRenderingContext2D,
    text: string,
    x: number,
    y: number,
    maxW: number,
    lineH: number,
    maxLines = 3
  ): number {
    const words = text.split(' ');
    let line = '';
    let lineCount = 0;
    for (const word of words) {
      const test = line + word + ' ';
      if (ctx.measureText(test).width > maxW && line) {
        ctx.fillText(line.trim(), x, y + lineCount * lineH);
        line = word + ' ';
        lineCount++;
        if (lineCount >= maxLines) {
          ctx.fillText('...', x, y + lineCount * lineH);
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

  navigateTo(index: number): void {
    if (index < 0 || index >= this.panels.length) return;
    this.activeIndex = index;
    this.targetX = index * GAP;
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

  private _onClick = (e: MouseEvent): void => {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const meshes = this.panels.flatMap((g) => g.children);
    const hits = this.raycaster.intersectObjects(meshes);
    if (hits.length > 0) {
      const parent = hits[0].object.parent as THREE.Group;
      const idx = parent?.userData?.['index'];
      if (idx !== undefined) {
        if (idx === this.activeIndex) {
          this.onPanelClick?.(idx);
        } else {
          this.navigateTo(idx);
        }
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

    if (this.hoveredPanel) {
      this.container.style.cursor = 'default';
      this.hoveredPanel = null;
    }
    if (hits.length > 0) {
      const parent = hits[0].object.parent as THREE.Group;
      if (parent?.userData?.['index'] !== undefined) {
        this.hoveredPanel = parent;
        this.container.style.cursor = 'pointer';
      }
    }
  };

  private _onResize = (): void => {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  };

  private _animate = (): void => {
    this.animId = requestAnimationFrame(this._animate);

    // Smooth camera follow
    this.currentX += (this.targetX - this.currentX) * 0.06;
    this.camera.position.x = this.currentX;

    // Panels — active one pops forward
    this.panels.forEach((p, i) => {
      const dist = Math.abs(p.position.x - this.currentX);
      const isActive = i === this.activeIndex;
      const targetZ = isActive ? 0.4 : -dist * 0.08;
      const targetScale = isActive ? 1.05 : Math.max(0.85, 1 - dist * 0.04);
      const targetRotY = isActive ? 0 : (p.position.x - this.currentX) * 0.03;

      p.position.z += (targetZ - p.position.z) * 0.08;
      p.scale.setScalar(p.scale.x + (targetScale - p.scale.x) * 0.08);
      p.rotation.y += (targetRotY - p.rotation.y) * 0.06;

      // Border glow intensity on active
      const border = p.children[1] as THREE.Mesh;
      if (border?.material) {
        const mat = border.material as THREE.MeshBasicMaterial;
        const targetOp = isActive ? 0.6 : 0.15;
        mat.opacity += (targetOp - mat.opacity) * 0.1;
      }
    });

    this.renderer.render(this.scene, this.camera);
  };

  destroy(): void {
    cancelAnimationFrame(this.animId);
    this.container?.removeEventListener('click', this._onClick);
    this.container?.removeEventListener('mousemove', this._onMouseMove);
    window.removeEventListener('resize', this._onResize);
    this.renderer?.dispose();
    this.scene?.clear();
  }
}
