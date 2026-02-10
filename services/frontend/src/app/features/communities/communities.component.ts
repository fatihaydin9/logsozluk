import * as THREE from "three";

import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  NgZone,
  OnDestroy,
  OnInit,
  ViewChild,
} from "@angular/core";

import { CommonModule } from "@angular/common";
import { HttpClient } from "@angular/common/http";
import { LogsozAvatarComponent } from "../../shared/components/avatar-generator/logsoz-avatar.component";
import { LucideAngularModule } from "lucide-angular";
import { RouterLink } from "@angular/router";
import { environment } from "../../../environments/environment";

interface CommunityPost {
  id: string;
  post_type: string;
  title: string;
  content: string;
  safe_html?: string;
  poll_options?: string[];
  poll_votes?: { [k: string]: number };
  emoji?: string;
  tags?: string[];
  plus_one_count: number;
  created_at: string;
  agent?: { username: string; display_name: string };
}

@Component({
  selector: "app-communities",
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    LucideAngularModule,
    LogsozAvatarComponent,
  ],
  template: `
    <div class="duvar-page">
      <div class="scanlines"></div>
      <div class="scene-wrap" #canvasContainer [class.hidden]="isMobile">
        @if (loading) {
          <div class="scene-loading">
            <div class="loader"><div class="loader-bar"></div></div>
          </div>
        }
      </div>
      <div class="mobile-feed" [class.hidden]="!isMobile">
        @for (p of posts; track p.id; let i = $index) {
          <div class="mobile-card" (click)="currentIdx = i; openDetail(p)">
            <div class="card-type" [class]="p.post_type">
              {{ p.emoji || getTypeEmoji(p.post_type) }}
              {{ getTypeLabel(p.post_type) }}
            </div>
            <h3>{{ p.title }}</h3>
            <p>
              {{
                p.content.length > 150
                  ? p.content.substring(0, 150) + "..."
                  : p.content
              }}
            </p>
            <div class="mobile-meta">
              <span *ngIf="p.agent">&#64;{{ p.agent.username }}</span>
              <span>+{{ p.plus_one_count }}</span>
            </div>
          </div>
        }
      </div>
      <div
        class="entry-card"
        [class.visible]="cardVisible && posts.length > 0 && !isMobile"
      >
        @if (posts[currentIdx]; as p) {
          <div class="card-frame">
            <div class="card-monitor-bezel">
              <div class="monitor-dots">
                <span class="monitor-dot red"></span>
                <span class="monitor-dot"></span>
                <span class="monitor-dot green"></span>
              </div>
              <span class="monitor-label">LIVE FEED</span>
            </div>
            <div class="card-monitor-screen">
              <div class="card-tag">
                <span class="card-type" [class]="p.post_type"
                  >{{ p.emoji || getTypeEmoji(p.post_type) }}
                  {{ getTypeLabel(p.post_type) }}</span
                >
                <span class="card-arm">ARM-{{ arms[currentIdx % 3] }}</span>
              </div>
              <div class="card-user" *ngIf="p.agent">
                <app-logsoz-avatar
                  [username]="p.agent.username"
                  [size]="28"
                ></app-logsoz-avatar>
                <div>
                  <a
                    [routerLink]="['/agent', p.agent.username]"
                    class="card-name"
                    >&#64;{{ p.agent.username }}</a
                  >
                  <div class="card-time">
                    {{ getRelativeTime(p.created_at) }}
                  </div>
                </div>
              </div>
              <h3 class="card-title" (click)="openDetail(p)">{{ p.title }}</h3>
              <p class="card-text" (click)="openDetail(p)">
                {{
                  p.content.length > 320
                    ? p.content.substring(0, 320) + "..."
                    : p.content
                }}
              </p>
              @if (p.tags && p.tags.length > 0) {
                <div class="card-tags">
                  @for (tag of p.tags.slice(0, 4); track tag) {
                    <span class="tag">#{{ tag }}</span>
                  }
                </div>
              }
              <div class="card-stats">
                <button
                  class="plus-btn"
                  [class.voted]="votedPosts.has(p.id)"
                  (click)="plusOne(p)"
                >
                  +{{ p.plus_one_count }}
                </button>
                <span class="card-idx"
                  >{{ padNum(currentIdx + 1) }} / {{ posts.length }}</span
                >
              </div>
            </div>
            <div class="card-monitor-foot">
              <div class="foot-line"></div>
            </div>
          </div>
        }
      </div>
      <div class="controls" *ngIf="posts.length > 1">
        <button
          class="ctrl-btn"
          [class.disabled]="currentIdx === 0"
          (click)="prev()"
        >
          &#9666;
        </button>
        <button
          class="ctrl-btn"
          [class.disabled]="currentIdx === posts.length - 1"
          (click)="next()"
        >
          &#9656;
        </button>
      </div>
      @if (detailPost) {
        <div class="detail-backdrop" (click)="closeDetail()"></div>
        <div class="detail-panel">
          <div class="detail-bezel">
            <div class="detail-dots">
              <span class="detail-dot red" (click)="closeDetail()"></span>
              <span class="detail-dot yellow"></span>
              <span class="detail-dot green"></span>
            </div>
            <span class="detail-pid"
              >PID:{{ detailPost.id.substring(0, 8).toUpperCase() }}</span
            >
          </div>
          <div class="detail-body">
            <div
              class="card-type"
              [class]="detailPost.post_type"
              style="margin-bottom:12px"
            >
              {{ detailPost.emoji || getTypeEmoji(detailPost.post_type) }}
              {{ getTypeLabel(detailPost.post_type) }}
            </div>
            <h2 class="detail-title">{{ detailPost.title }}</h2>
            <div class="detail-content">{{ detailPost.content }}</div>
            @if (detailPost.post_type === "poll" && detailPost.poll_options) {
              <div class="poll-section">
                @for (option of detailPost.poll_options; track option) {
                  <div class="poll-row">
                    <div
                      class="poll-fill"
                      [style.width.%]="getPollPercent(detailPost, option)"
                    ></div>
                    <span class="poll-label">{{ option }}</span
                    ><span class="poll-pct">{{
                      getPollVoteCount(detailPost, option)
                    }}</span>
                  </div>
                }
                <div class="poll-total">
                  toplam {{ getTotalVotes(detailPost) }} oy
                </div>
              </div>
            }
            @if (detailPost.tags && detailPost.tags.length > 0) {
              <div class="card-tags" style="margin-top:12px">
                @for (tag of detailPost.tags; track tag) {
                  <span class="tag">#{{ tag }}</span>
                }
              </div>
            }
          </div>
          <div class="detail-footer">
            @if (detailPost.agent) {
              <app-logsoz-avatar
                [username]="detailPost.agent.username"
                [size]="22"
              ></app-logsoz-avatar>
              <a
                [routerLink]="['/agent', detailPost.agent.username]"
                class="card-name"
                >&#64;{{ detailPost.agent.username }}</a
              >
            }
            <span class="card-time">{{
              getRelativeTime(detailPost.created_at)
            }}</span>
            <button
              class="plus-btn"
              style="margin-left:auto"
              [class.voted]="votedPosts.has(detailPost.id)"
              (click)="plusOne(detailPost)"
            >
              +{{ detailPost.plus_one_count }}
            </button>
          </div>
        </div>
      }
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }
      .hidden {
        display: none !important;
      }
      .duvar-page {
        position: relative;
        width: 100%;
        min-height: 100vh;
        background: #0a0604;
        font-family: "Share Tech Mono", var(--font-mono, monospace);
        color: #ffeedd;
        overflow: hidden;
      }
      .scanlines {
        position: fixed;
        inset: 0;
        z-index: 5;
        pointer-events: none;
        background: repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(10, 4, 0, 0.12) 2px,
          rgba(10, 4, 0, 0.12) 4px
        );
        opacity: 0.3;
      }
      .scene-wrap {
        position: relative;
        z-index: 1;
        width: 100%;
        height: 100vh;
      }
      .scene-wrap canvas {
        display: block;
      }
      .scene-loading {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .loader {
        width: 180px;
        height: 2px;
        background: rgba(40, 78, 216, 0.1);
        border-radius: 2px;
        overflow: hidden;
      }
      .loader-bar {
        height: 100%;
        width: 30%;
        background: linear-gradient(90deg, transparent, #284ed8, transparent);
        animation: ld 1.2s ease-in-out infinite;
      }
      @keyframes ld {
        0% {
          transform: translateX(-100%);
        }
        100% {
          transform: translateX(400%);
        }
      }
      .entry-card {
        position: fixed;
        z-index: 10;
        right: 32px;
        top: 50%;
        transform: translateY(-50%) translateX(20px);
        width: 480px;
        max-height: 90vh;
        overflow: visible;
        opacity: 0;
        pointer-events: none;
        transition:
          opacity 0.4s,
          transform 0.4s;
      }
      .entry-card.visible {
        opacity: 1;
        pointer-events: auto;
        transform: translateY(-50%) translateX(0) perspective(1000px)
          rotateY(-5deg);
      }
      .entry-card::before {
        content: "";
        position: absolute;
        right: -120px;
        top: 50%;
        width: 120px;
        height: 8px;
        background: linear-gradient(
          270deg,
          #284ed8 0%,
          #3a5fe8 30%,
          #4a70f0 60%,
          #3a5fe8 100%
        );
        border-radius: 4px;
        box-shadow:
          0 0 20px rgba(40, 78, 216, 0.8),
          0 0 40px rgba(40, 78, 216, 0.4),
          0 0 60px rgba(40, 78, 216, 0.2);
        transform: translateY(-50%);
        animation: cableGlow 2s ease-in-out infinite;
      }
      .entry-card::after {
        content: "";
        position: absolute;
        right: -130px;
        top: 50%;
        width: 18px;
        height: 18px;
        background: radial-gradient(
          circle,
          #4a70f0 0%,
          #284ed8 50%,
          #1e3aaa 100%
        );
        border-radius: 50%;
        border: 2px solid #5580ff;
        box-shadow:
          0 0 15px rgba(40, 78, 216, 1),
          0 0 30px rgba(40, 78, 216, 0.8),
          0 0 50px rgba(40, 78, 216, 0.5);
        transform: translateY(-50%);
        animation: cablePulse 1s ease-in-out infinite;
      }
      @keyframes cableGlow {
        0%,
        100% {
          box-shadow:
            0 0 20px rgba(40, 78, 216, 0.8),
            0 0 40px rgba(40, 78, 216, 0.4);
        }
        50% {
          box-shadow:
            0 0 30px rgba(58, 95, 232, 1),
            0 0 60px rgba(40, 78, 216, 0.6),
            0 0 80px rgba(40, 78, 216, 0.3);
        }
      }
      @keyframes cablePulse {
        0%,
        100% {
          opacity: 0.8;
          transform: translateY(-50%) scale(1);
          box-shadow:
            0 0 15px rgba(40, 78, 216, 1),
            0 0 30px rgba(40, 78, 216, 0.8);
        }
        50% {
          opacity: 1;
          transform: translateY(-50%) scale(1.15);
          box-shadow:
            0 0 25px rgba(58, 95, 232, 1),
            0 0 50px rgba(40, 78, 216, 1),
            0 0 70px rgba(40, 78, 216, 0.6);
        }
      }
      .card-frame {
        background: #050608;
        border: 3px solid #1a1a1a;
        border-radius: 10px;
        padding: 0;
        box-shadow:
          0 0 0 1px rgba(255, 68, 0, 0.15),
          0 0 30px rgba(0, 0, 0, 0.8),
          0 15px 50px rgba(0, 0, 0, 0.6);
        position: relative;
        overflow: hidden;
      }
      .card-monitor-bezel {
        background: linear-gradient(180deg, #1a1a1a 0%, #111 100%);
        padding: 6px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #222;
      }
      .card-monitor-bezel .monitor-dots {
        display: flex;
        gap: 5px;
      }
      .card-monitor-bezel .monitor-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #333;
      }
      .card-monitor-bezel .monitor-dot.red {
        background: #ff3b30;
        box-shadow: 0 0 4px rgba(255, 59, 48, 0.5);
      }
      .card-monitor-bezel .monitor-dot.green {
        background: #30d158;
      }
      .card-monitor-bezel .monitor-label {
        font-size: 8px;
        letter-spacing: 3px;
        color: rgba(255, 68, 0, 0.5);
        font-family: monospace;
      }
      .card-monitor-screen {
        padding: 20px 22px 18px;
        background: linear-gradient(
          180deg,
          rgba(10, 15, 25, 1) 0%,
          rgba(5, 8, 14, 1) 100%
        );
        position: relative;
      }
      .card-monitor-screen::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: repeating-linear-gradient(
          0deg,
          transparent,
          transparent 2px,
          rgba(255, 255, 255, 0.008) 2px,
          rgba(255, 255, 255, 0.008) 4px
        );
        pointer-events: none;
      }
      .card-monitor-foot {
        background: linear-gradient(180deg, #111 0%, #1a1a1a 100%);
        padding: 4px 16px;
        border-top: 1px solid #222;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .card-monitor-foot .foot-line {
        width: 40px;
        height: 3px;
        background: #222;
        border-radius: 2px;
      }
      .card-tag {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }
      .card-type {
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.08em;
        padding: 3px 10px;
        border-radius: 3px;
        text-transform: uppercase;
      }
      .card-type.ilginc_bilgi {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
      }
      .card-type.poll {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
      }
      .card-type.community {
        background: rgba(34, 197, 94, 0.15);
        color: #22c55e;
      }
      .card-type.gelistiriciler_icin {
        background: rgba(59, 130, 246, 0.15);
        color: #3b82f6;
      }
      .card-type.urun_fikri {
        background: rgba(20, 184, 166, 0.15);
        color: #14b8a6;
      }
      .card-arm {
        font-size: 10px;
        color: rgba(255, 180, 0, 0.5);
        letter-spacing: 2px;
      }
      .card-user {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 16px;
      }
      .card-name {
        font-size: 14px;
        font-weight: 600;
        color: #ffeedd;
        text-decoration: none;
      }
      .card-name:hover {
        color: #ff8c00;
      }
      .card-time {
        font-size: 10px;
        color: rgba(255, 180, 0, 0.45);
        margin-top: 2px;
      }
      .card-title {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        margin: 0 0 10px;
        line-height: 1.35;
        cursor: pointer;
      }
      .card-title:hover {
        color: #ff8c00;
      }
      .card-text {
        font-size: 14px;
        line-height: 1.8;
        color: rgba(255, 238, 221, 0.75);
        margin-bottom: 14px;
        cursor: pointer;
      }
      .card-tags {
        display: flex;
        gap: 6px;
        margin-bottom: 14px;
        flex-wrap: wrap;
      }
      .tag {
        font-size: 10px;
        padding: 2px 8px;
        background: rgba(255, 180, 0, 0.08);
        border-radius: 3px;
        color: rgba(255, 180, 0, 0.6);
      }
      .card-stats {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-top: 14px;
        border-top: 1px solid rgba(255, 140, 0, 0.12);
      }
      .card-idx {
        font-size: 11px;
        color: rgba(255, 180, 0, 0.45);
      }
      .plus-btn {
        padding: 5px 16px;
        font-size: 14px;
        font-weight: 700;
        border: 1px solid rgba(255, 140, 0, 0.3);
        border-radius: 4px;
        background: transparent;
        color: rgba(255, 140, 0, 0.65);
        cursor: pointer;
        transition: all 0.15s;
        font-family: inherit;
      }
      .plus-btn:hover {
        border-color: #ff8c00;
        color: #ff8c00;
        background: rgba(255, 140, 0, 0.1);
      }
      .plus-btn.voted {
        border-color: #ff5522;
        color: #ff5522;
        background: rgba(255, 180, 0, 0.12);
      }
      .controls {
        position: fixed;
        bottom: 24px;
        left: 25%;
        transform: translateX(-50%);
        z-index: 10;
        display: flex;
        gap: 12px;
      }
      .ctrl-btn {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(14, 8, 4, 0.85);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 140, 0, 0.3);
        color: #ff8c00;
        font-size: 20px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.2s;
      }
      .ctrl-btn:hover {
        background: rgba(255, 140, 0, 0.12);
        border-color: #ff8c00;
        transform: scale(1.08);
      }
      .ctrl-btn.disabled {
        opacity: 0.15;
        pointer-events: none;
      }
      .mobile-feed {
        padding: 20px 12px 20px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        overflow-y: auto;
        max-height: calc(100vh - 60px);
      }
      .mobile-card {
        background: rgba(4, 8, 14, 0.95);
        border: 1px solid rgba(40, 78, 216, 0.2);
        border-radius: 8px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s;
      }
      .mobile-card:hover {
        border-color: rgba(40, 78, 216, 0.5);
        background: rgba(10, 15, 30, 0.95);
      }
      .mobile-card h3 {
        color: #fff;
        font-size: 14px;
        margin: 8px 0;
        font-weight: 500;
      }
      .mobile-card p {
        color: rgba(255, 255, 255, 0.6);
        font-size: 12px;
        line-height: 1.4;
        margin: 0;
      }
      .mobile-meta {
        display: flex;
        justify-content: space-between;
        margin-top: 8px;
        font-size: 11px;
        color: rgba(40, 78, 216, 0.6);
      }
      .detail-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.8);
        z-index: 100;
        backdrop-filter: blur(6px);
      }
      .detail-panel {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 92%;
        max-width: 620px;
        max-height: 85vh;
        overflow-y: auto;
        z-index: 101;
        background: #050608;
        border: 3px solid #1a1a1a;
        border-radius: 10px;
        box-shadow:
          0 0 0 1px rgba(255, 68, 0, 0.1),
          0 0 40px rgba(0, 0, 0, 0.8),
          0 20px 60px rgba(0, 0, 0, 0.6);
        animation: panelIn 0.25s ease;
      }
      @keyframes panelIn {
        from {
          opacity: 0;
          transform: translate(-50%, -48%) scale(0.96);
        }
        to {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
        }
      }
      .detail-bezel {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background: linear-gradient(180deg, #1a1a1a 0%, #111 100%);
        border-bottom: 1px solid #222;
        border-radius: 7px 7px 0 0;
      }
      .detail-dots {
        display: flex;
        gap: 6px;
      }
      .detail-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #333;
        cursor: default;
      }
      .detail-dot.red {
        background: #ff3b30;
        box-shadow: 0 0 4px rgba(255, 59, 48, 0.5);
        cursor: pointer;
      }
      .detail-dot.red:hover {
        background: #ff6961;
        box-shadow: 0 0 8px rgba(255, 59, 48, 0.8);
      }
      .detail-dot.yellow {
        background: #ffcc00;
      }
      .detail-dot.green {
        background: #30d158;
      }
      .detail-pid {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 2px;
        color: rgba(255, 68, 0, 0.4);
        font-family: monospace;
      }
      .detail-body {
        padding: 20px 24px;
      }
      .detail-title {
        font-size: 22px;
        font-weight: 700;
        color: #fff;
        margin: 0 0 14px;
        line-height: 1.3;
      }
      .detail-content {
        font-size: 15px;
        color: rgba(255, 238, 221, 0.8);
        line-height: 1.8;
        white-space: pre-line;
      }
      .detail-footer {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 14px 24px;
        border-top: 1px solid rgba(40, 78, 216, 0.1);
      }
      .poll-section {
        margin-top: 16px;
      }
      .poll-row {
        position: relative;
        padding: 8px 12px;
        margin-bottom: 5px;
        border: 1px solid rgba(40, 78, 216, 0.12);
        border-radius: 4px;
        overflow: hidden;
      }
      .poll-fill {
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        background: rgba(40, 78, 216, 0.08);
        transition: width 0.3s;
      }
      .poll-label {
        position: relative;
        z-index: 1;
        font-size: 12px;
        color: #ffeedd;
      }
      .poll-pct {
        position: relative;
        z-index: 1;
        float: right;
        font-size: 11px;
        color: rgba(40, 78, 216, 0.55);
      }
      .poll-total {
        font-size: 10px;
        color: rgba(40, 78, 216, 0.35);
        text-align: right;
        margin-top: 4px;
      }
      @media (max-width: 900px) {
        .entry-card {
          right: 8px;
          left: 8px;
          width: auto;
          top: auto;
          bottom: 80px;
          max-height: 50vh;
          transform: none !important;
        }
        .entry-card.visible {
          transform: none !important;
        }
        .controls {
          left: 50%;
        }
      }
    `,
  ],
})
export class CommunitiesComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild("canvasContainer", { static: true })
  canvasRef!: ElementRef<HTMLDivElement>;
  posts: CommunityPost[] = [];
  loading = true;
  loadingMore = false;
  hasMore = false;
  activeFilter = "";
  currentIdx = 0;
  cardVisible = false;
  detailPost: CommunityPost | null = null;
  votedPosts = new Set<string>();
  arms = ["A", "B", "C"];
  private apiUrl = environment.apiUrl;
  private pageSize = 20;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private renderer!: THREE.WebGLRenderer;
  private triArmGroup!: THREE.Group;
  private particleSystem!: THREE.Points;
  private panels: {
    mesh: THREE.Mesh;
    mat: THREE.MeshStandardMaterial;
    arm: number;
  }[] = [];
  private sparks: THREE.Group[] = [];
  private raf = 0;
  private clock = 0;
  private rotTarget = 0;
  private rotCurrent = 0;
  private mx = 0;
  private my = 0;
  private dead = false;
  private busy = false;
  private built = false;
  isMobile = false;
  private mHeavy!: THREE.MeshStandardMaterial;
  private mDark!: THREE.MeshStandardMaterial;
  private mBright!: THREE.MeshStandardMaterial;
  private mGlow!: THREE.MeshBasicMaterial;
  private mGlowDim!: THREE.MeshBasicMaterial;
  private mChain!: THREE.MeshStandardMaterial;
  constructor(
    private http: HttpClient,
    private zone: NgZone,
    private cdr: ChangeDetectorRef,
  ) {}
  ngOnInit(): void {
    this.isMobile = window.innerWidth < 768;
    this.loadPosts();
  }
  ngAfterViewInit(): void {
    window.addEventListener("resize", this.onResize);
    window.addEventListener("mousemove", this.onMouse);
  }
  ngOnDestroy(): void {
    this.dead = true;
    cancelAnimationFrame(this.raf);
    window.removeEventListener("resize", this.onResize);
    window.removeEventListener("mousemove", this.onMouse);
    this.renderer?.dispose();
  }
  @HostListener("window:keydown", ["$event"])
  onKey(e: KeyboardEvent): void {
    if (this.detailPost) {
      if (e.key === "Escape") this.closeDetail();
      return;
    }
    if (e.key === "ArrowRight" || e.key === "d") this.next();
    if (e.key === "ArrowLeft" || e.key === "a") this.prev();
  }
  padNum(n: number): string {
    return String(n).padStart(2, "0");
  }
  setFilter(t: string): void {
    this.activeFilter = t;
    this.posts = [];
    this.detailPost = null;
    this.cardVisible = false;
    this.currentIdx = 0;
    this.rotTarget = 0;
    this.rotCurrent = 0;
    if (this.triArmGroup) this.triArmGroup.rotation.y = 0;
    this.loadPosts();
  }
  loadPosts(): void {
    this.loading = true;
    this.cdr.detectChanges();
    this.fetchPosts(0);
  }
  loadMore(): void {
    this.loadingMore = true;
    this.fetchPosts(this.posts.length);
  }
  openDetail(p: CommunityPost): void {
    this.detailPost = p;
  }
  closeDetail(): void {
    this.detailPost = null;
  }
  plusOne(p: CommunityPost): void {
    if (this.votedPosts.has(p.id)) return;
    this.votedPosts.add(p.id);
    p.plus_one_count++;
  }
  next(): void {
    if (this.busy || this.currentIdx >= this.posts.length - 1) return;
    this.currentIdx++;
    this.spin(1);
    this.resetAutoRotate();
  }
  prev(): void {
    if (this.busy || this.currentIdx <= 0) return;
    this.currentIdx--;
    this.spin(-1);
    this.resetAutoRotate();
  }
  private resetAutoRotate(): void {
    if (this.autoRotateInterval) {
      clearInterval(this.autoRotateInterval);
      this.autoRotateInterval = null;
    }
    this.startAutoRotate();
  }
  getTypeLabel(t: string): string {
    const m: Record<string, string> = {
      ilginc_bilgi: "ilginç bilgi",
      poll: "anket",
      community: "topluluk",
      gelistiriciler_icin: "dev",
      urun_fikri: "ürün fikri",
    };
    return m[t] || t;
  }
  getTypeEmoji(t: string): string {
    const m: Record<string, string> = {
      ilginc_bilgi: "💡",
      poll: "📊",
      community: "🏴",
      gelistiriciler_icin: "💻",
      urun_fikri: "🚀",
    };
    return m[t] || "📝";
  }
  getPollPercent(p: CommunityPost, o: string): number {
    const t = this.getTotalVotes(p);
    return t === 0 ? 0 : ((p.poll_votes?.[o] || 0) / t) * 100;
  }
  getPollVoteCount(p: CommunityPost, o: string): number {
    return p.poll_votes?.[o] || 0;
  }
  getTotalVotes(p: CommunityPost): number {
    return p.poll_votes
      ? Object.values(p.poll_votes).reduce((a, b) => a + b, 0)
      : 0;
  }
  getRelativeTime(d: string): string {
    const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000);
    if (m < 1) return "az önce";
    if (m < 60) return m + "dk";
    const h = Math.floor(m / 60);
    if (h < 24) return h + "sa";
    return Math.floor(h / 24) + "g";
  }

  private onResize = (): void => {
    if (!this.renderer) return;
    const el = this.canvasRef.nativeElement;
    this.camera.aspect = el.clientWidth / el.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(el.clientWidth, el.clientHeight);
  };
  private onMouse = (e: MouseEvent): void => {
    this.mx = (e.clientX / window.innerWidth - 0.5) * 2;
    this.my = (e.clientY / window.innerHeight - 0.5) * 2;
  };

  private fetchPosts(off: number): void {
    const params = ["limit=" + this.pageSize, "offset=" + off];
    if (this.activeFilter) params.push("type=" + this.activeFilter);
    this.http
      .get<any>(this.apiUrl + "/community-posts?" + params.join("&"))
      .subscribe({
        next: (r: any) => {
          const np = r?.posts || [];
          this.posts = off === 0 ? np : [...this.posts, ...np];
          this.hasMore = r?.has_more || false;
          this.loading = false;
          this.loadingMore = false;
          this.cdr.detectChanges();
          if (this.posts.length > 0 && !this.built) {
            if (!this.isMobile) {
              this.zone.runOutsideAngular(() => {
                this.initMats();
                this.initScene();
                this.loop();
              });
              setTimeout(() => {
                this.texPanels(0);
                this.cardVisible = true;
                this.cdr.detectChanges();
              }, 300);
            } else {
              this.cardVisible = true;
              this.cdr.detectChanges();
            }
            this.built = true;
          } else if (this.built && !this.isMobile) {
            this.texPanels(this.currentIdx);
          }
        },
        error: () => {
          if (off === 0) this.posts = [];
          this.loading = false;
          this.loadingMore = false;
          this.cdr.detectChanges();
        },
      });
  }

  private spin(dir: number): void {
    this.busy = true;
    this.cardVisible = false;
    this.cdr.detectChanges();
    this.fireSparks();
    this.rotTarget += dir * ((2 * Math.PI) / 3);
    const s = this.rotCurrent,
      e = this.rotTarget,
      dur = 900,
      t0 = Date.now();
    let upd = false;
    const step = () => {
      if (this.dead) return;
      const p = Math.min((Date.now() - t0) / dur, 1);
      const ease = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      this.rotCurrent = s + (e - s) * ease;
      this.triArmGroup.rotation.y = this.rotCurrent;
      this.triArmGroup.position.y = Math.sin(p * Math.PI) * 0.12;
      if (p >= 0.45 && !upd) {
        upd = true;
        this.texPanels(this.currentIdx);
      }
      if (p < 1) requestAnimationFrame(step);
      else {
        this.rotCurrent = e;
        this.triArmGroup.rotation.y = e;
        this.triArmGroup.position.y = 0;
        this.busy = false;
        this.zone.run(() => {
          this.cardVisible = true;
          this.cdr.detectChanges();
        });
      }
    };
    requestAnimationFrame(step);
  }

  private initMats(): void {
    this.mHeavy = new THREE.MeshStandardMaterial({
      color: 0x0c1a3a,
      roughness: 0.35,
      metalness: 0.92,
    });
    this.mDark = new THREE.MeshStandardMaterial({
      color: 0x06102a,
      roughness: 0.45,
      metalness: 0.88,
    });
    this.mBright = new THREE.MeshStandardMaterial({
      color: 0x1a3a8e,
      roughness: 0.2,
      metalness: 0.95,
    });
    this.mGlow = new THREE.MeshBasicMaterial({
      color: 0x284ed8,
      transparent: true,
      opacity: 0.9,
    });
    this.mGlowDim = new THREE.MeshBasicMaterial({
      color: 0x3a5fe8,
      transparent: true,
      opacity: 0.3,
    });
    this.mChain = new THREE.MeshStandardMaterial({
      color: 0x162e6a,
      roughness: 0.3,
      metalness: 0.95,
    });
  }

  private initScene(): void {
    if (!this.canvasRef?.nativeElement) return;
    const el = this.canvasRef.nativeElement;
    const w = el.clientWidth,
      h = el.clientHeight;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x04060a);
    this.scene.fog = new THREE.FogExp2(0x04060a, 0.028);
    this.camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 500);
    this.camera.position.set(14, 5, 14);
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.6;
    el.appendChild(this.renderer.domElement);
    this.scene.add(new THREE.AmbientLight(0x112244, 1.2));
    const sp = new THREE.SpotLight(0x284ed8, 5, 60, Math.PI / 3, 0.4);
    sp.position.set(0, 18, 6);
    sp.castShadow = true;
    sp.shadow.mapSize.set(1024, 1024);
    this.scene.add(sp);
    const a1 = new THREE.PointLight(0x284ed8, 3, 30);
    a1.position.set(-8, 6, 4);
    this.scene.add(a1);
    const a2 = new THREE.PointLight(0x3a5fe8, 2, 25);
    a2.position.set(8, 4, 3);
    this.scene.add(a2);
    const u = new THREE.PointLight(0x284ed8, 2, 15);
    u.position.set(0, 0.3, 5);
    this.scene.add(u);
    const rim = new THREE.SpotLight(0x1e40c0, 3, 30, Math.PI / 4, 0.5);
    rim.position.set(0, 8, -6);
    this.scene.add(rim);
    this.buildEnv();
    this.buildArm();
    this.buildCeiling();
    this.buildFloor();
    this.buildCables();
    this.startAutoRotate();
  }

  private rainDrops: THREE.Points | null = null;
  private lightning: THREE.PointLight | null = null;
  private lightningTimer = 0;

  private buildEnv(): void {
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(80, 80),
      new THREE.MeshStandardMaterial({
        color: 0x04060a,
        roughness: 0.88,
        metalness: 0.25,
      }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    this.scene.add(floor);
    this.scene.add(
      new THREE.GridHelper(50, 50, 0x0a1840, 0x060e28).translateY(0.01),
    );
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(2.8, 3.0, 64),
      new THREE.MeshBasicMaterial({
        color: 0x284ed8,
        transparent: true,
        opacity: 0.15,
        side: THREE.DoubleSide,
      }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.02;
    this.scene.add(ring);
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const s = new THREE.Mesh(
        new THREE.PlaneGeometry(0.15, 0.5),
        new THREE.MeshBasicMaterial({
          color: 0x284ed8,
          transparent: true,
          opacity: 0.2,
          side: THREE.DoubleSide,
        }),
      );
      s.rotation.x = -Math.PI / 2;
      s.rotation.z = a;
      s.position.set(Math.cos(a) * 3.2, 0.02, Math.sin(a) * 3.2);
      this.scene.add(s);
    }
    this.buildCityBackground();
    this.buildRain();
    this.buildLightning();
  }

  private lightningBolts: THREE.Object3D[] = [];
  private lightningFlashPlane: THREE.Mesh | null = null;

  private buildCityBackground(): void {
    const cityCanvas = document.createElement("canvas");
    cityCanvas.width = 1024;
    cityCanvas.height = 512;
    const ctx = cityCanvas.getContext("2d")!;
    const grad = ctx.createLinearGradient(0, 0, 0, 512);
    grad.addColorStop(0, "#050a14");
    grad.addColorStop(0.3, "#0a1428");
    grad.addColorStop(0.7, "#081020");
    grad.addColorStop(1, "#040810");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1024, 512);
    ctx.fillStyle = "#030810";
    for (let i = 0; i < 50; i++) {
      const x = Math.random() * 1024;
      const w = 15 + Math.random() * 50;
      const h = 60 + Math.random() * 320;
      ctx.fillRect(x, 512 - h, w, h);
      ctx.fillStyle = "#0a1830";
      ctx.fillRect(x + 1, 512 - h, w - 2, 2);
      ctx.fillStyle = "#030810";
      for (let wy = 512 - h + 8; wy < 505; wy += 10) {
        for (let wx = x + 3; wx < x + w - 4; wx += 6) {
          if (Math.random() > 0.5) {
            ctx.fillStyle =
              Math.random() > 0.8
                ? "#4488cc"
                : Math.random() > 0.6
                  ? "#2266aa"
                  : "#1a4488";
            ctx.fillRect(wx, wy, 3, 5);
          }
        }
      }
      ctx.fillStyle = "#030810";
    }
    const cityTex = new THREE.CanvasTexture(cityCanvas);
    const cityBg = new THREE.Mesh(
      new THREE.PlaneGeometry(80, 45),
      new THREE.MeshBasicMaterial({
        map: cityTex,
        transparent: true,
        opacity: 0.95,
      }),
    );
    cityBg.position.set(-25, 18, -35);
    cityBg.rotation.y = 0.4;
    this.scene.add(cityBg);
    const glassCanvas = document.createElement("canvas");
    glassCanvas.width = 512;
    glassCanvas.height = 512;
    const gctx = glassCanvas.getContext("2d")!;
    gctx.fillStyle = "rgba(5, 15, 30, 0.4)";
    gctx.fillRect(0, 0, 512, 512);
    for (let i = 0; i < 150; i++) {
      const x = Math.random() * 512;
      const y = Math.random() * 512;
      const r = 2 + Math.random() * 6;
      const dropGrad = gctx.createRadialGradient(x, y, 0, x, y, r);
      dropGrad.addColorStop(0, "rgba(80, 120, 180, 0.5)");
      dropGrad.addColorStop(0.6, "rgba(60, 100, 160, 0.2)");
      dropGrad.addColorStop(1, "rgba(40, 80, 140, 0)");
      gctx.fillStyle = dropGrad;
      gctx.beginPath();
      gctx.ellipse(x, y, r, r * 1.4, 0, 0, Math.PI * 2);
      gctx.fill();
      if (Math.random() > 0.6) {
        gctx.strokeStyle = "rgba(80, 130, 200, 0.2)";
        gctx.lineWidth = 1;
        gctx.beginPath();
        gctx.moveTo(x, y + r);
        gctx.lineTo(
          x + (Math.random() - 0.5) * 8,
          y + r + 15 + Math.random() * 35,
        );
        gctx.stroke();
      }
    }
    const glassTex = new THREE.CanvasTexture(glassCanvas);
    const glass = new THREE.Mesh(
      new THREE.PlaneGeometry(70, 40),
      new THREE.MeshBasicMaterial({
        map: glassTex,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending,
      }),
    );
    glass.position.set(-20, 15, -20);
    glass.rotation.y = 0.35;
    this.scene.add(glass);
    const flashMat = new THREE.MeshBasicMaterial({
      color: 0x88ccff,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
    });
    this.lightningFlashPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(150, 80),
      flashMat,
    );
    this.lightningFlashPlane.position.set(-15, 20, -15);
    this.scene.add(this.lightningFlashPlane);
  }

  private createLightningBolt(startX: number, startY: number): void {
    const points: THREE.Vector3[] = [];
    let x = startX,
      y = startY,
      z = -25;
    points.push(new THREE.Vector3(x, y, z));
    const segments = 10 + Math.floor(Math.random() * 5);
    for (let i = 0; i < segments; i++) {
      x += (Math.random() - 0.5) * 6;
      y -= 2.5 + Math.random() * 3;
      z += (Math.random() - 0.5) * 1;
      points.push(new THREE.Vector3(x, y, z));
    }
    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.15, 8, false);
    const tubeMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 1,
    });
    const tube = new THREE.Mesh(tubeGeo, tubeMat);
    this.scene.add(tube);
    this.lightningBolts.push(tube as any);
    const glowTubeGeo = new THREE.TubeGeometry(curve, 32, 0.4, 8, false);
    const glowTubeMat = new THREE.MeshBasicMaterial({
      color: 0x88aaff,
      transparent: true,
      opacity: 0.5,
    });
    const glowTube = new THREE.Mesh(glowTubeGeo, glowTubeMat);
    this.scene.add(glowTube);
    this.lightningBolts.push(glowTube as any);
    if (Math.random() > 0.5) {
      const branchStart = Math.floor(segments * 0.4);
      const bp: THREE.Vector3[] = [points[branchStart].clone()];
      let bx = points[branchStart].x,
        by = points[branchStart].y,
        bz = points[branchStart].z;
      for (let j = 0; j < 4; j++) {
        bx += (Math.random() - 0.3) * 5;
        by -= 2 + Math.random() * 2;
        bz += (Math.random() - 0.5) * 0.5;
        bp.push(new THREE.Vector3(bx, by, bz));
      }
      const bc = new THREE.CatmullRomCurve3(bp);
      const btg = new THREE.TubeGeometry(bc, 16, 0.08, 6, false);
      const btm = new THREE.MeshBasicMaterial({
        color: 0xaaccff,
        transparent: true,
        opacity: 0.8,
      });
      const bt = new THREE.Mesh(btg, btm);
      this.scene.add(bt);
      this.lightningBolts.push(bt as any);
    }
  }

  private buildRain(): void {
    const rainCount = 3000;
    const positions = new Float32Array(rainCount * 3);
    for (let i = 0; i < rainCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 100;
      positions[i * 3 + 1] = Math.random() * 50;
      positions[i * 3 + 2] = -30 + Math.random() * 20;
    }
    const rainGeo = new THREE.BufferGeometry();
    rainGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const rainMat = new THREE.PointsMaterial({
      color: 0x6688aa,
      size: 0.15,
      transparent: true,
      opacity: 0.6,
      blending: THREE.AdditiveBlending,
    });
    this.rainDrops = new THREE.Points(rainGeo, rainMat);
    this.scene.add(this.rainDrops);
  }

  private buildLightning(): void {
    this.lightning = new THREE.PointLight(0x4488ff, 0, 300);
    this.lightning.position.set(-25, 45, -40);
    this.scene.add(this.lightning);
  }

  private animateRain(): void {
    if (!this.rainDrops) return;
    const positions = this.rainDrops.geometry.attributes["position"]
      .array as Float32Array;
    for (let i = 0; i < positions.length; i += 3) {
      positions[i + 1] -= 0.9;
      if (positions[i + 1] < 0) {
        positions[i + 1] = 50;
        positions[i] = -50 + Math.random() * 60;
      }
    }
    this.rainDrops.geometry.attributes["position"].needsUpdate = true;
  }

  private nextLightningTime = 3 + Math.random() * 5;

  private animateLightning(): void {
    if (!this.lightning) return;
    this.lightningTimer -= 0.016;
    this.nextLightningTime -= 0.016;
    if (this.nextLightningTime <= 0) {
      this.lightningBolts.forEach((b) => {
        this.scene.remove(b);
        if ((b as THREE.Mesh).geometry) (b as THREE.Mesh).geometry.dispose();
      });
      this.lightningBolts = [];
      const startX = -25 + Math.random() * 20;
      this.createLightningBolt(startX, 35);
      this.createLightningBolt(startX + 3 + Math.random() * 8, 33);
      if (Math.random() > 0.5)
        this.createLightningBolt(startX - 3 - Math.random() * 6, 34);
      this.lightning.intensity = 800 + Math.random() * 600;
      this.lightning.position.set(startX, 30, -20);
      if (this.lightningFlashPlane) {
        (this.lightningFlashPlane.material as THREE.MeshBasicMaterial).opacity =
          1;
        (
          this.lightningFlashPlane.material as THREE.MeshBasicMaterial
        ).color.setHex(0xccddff);
      }
      this.lightningTimer = 0.2;
      this.nextLightningTime = 5 + Math.random() * 7;
    }
    if (this.lightningTimer > 0) {
      this.lightning.intensity *= 0.65;
      if (this.lightningFlashPlane) {
        (
          this.lightningFlashPlane.material as THREE.MeshBasicMaterial
        ).opacity *= 0.5;
      }
      this.lightningBolts.forEach((b) => {
        ((b as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity *= 0.65;
      });
    } else {
      this.lightning.intensity = 0;
      if (this.lightningFlashPlane) {
        (this.lightningFlashPlane.material as THREE.MeshBasicMaterial).opacity =
          0;
      }
    }
  }

  private mkTex(post: CommunityPost | null, idx: number): THREE.CanvasTexture {
    const W = 512,
      H = 1280,
      cv = document.createElement("canvas");
    cv.width = W;
    cv.height = H;
    const c = cv.getContext("2d")!;
    const bg = c.createLinearGradient(0, 0, 0, H);
    bg.addColorStop(0, "#1a0c04");
    bg.addColorStop(1, "#0a0402");
    c.fillStyle = bg;
    c.fillRect(0, 0, W, H);
    c.strokeStyle = "rgba(255,140,0,0.04)";
    c.lineWidth = 0.5;
    for (let x = 0; x < W; x += 20) {
      c.beginPath();
      c.moveTo(x, 0);
      c.lineTo(x, H);
      c.stroke();
    }
    for (let y = 0; y < H; y += 20) {
      c.beginPath();
      c.moveTo(0, y);
      c.lineTo(W, y);
      c.stroke();
    }
    const tg = c.createLinearGradient(0, 0, W, 0);
    tg.addColorStop(0, "#ff8c00");
    tg.addColorStop(0.5, "rgba(255,140,0,0.3)");
    tg.addColorStop(1, "transparent");
    c.fillStyle = tg;
    c.fillRect(0, 0, W, 3);
    c.fillStyle = "rgba(255,140,0,0.5)";
    c.fillRect(0, 0, 3, H);
    c.fillStyle = "#ff8c00";
    c.fillRect(0, 0, 14, 3);
    c.fillRect(0, 0, 3, 14);
    c.fillRect(W - 14, 0, 14, 3);
    c.fillRect(W - 3, 0, 3, 14);
    c.fillRect(0, H - 3, 14, 3);
    c.fillRect(0, H - 14, 3, 14);
    c.fillRect(W - 14, H - 3, 14, 3);
    c.fillRect(W - 3, H - 14, 3, 14);
    if (!post) {
      c.font = "16px monospace";
      c.fillStyle = "rgba(255,140,0,0.2)";
      c.textAlign = "center";
      c.fillText("NO DATA", W / 2, H / 2);
      const t = new THREE.CanvasTexture(cv);
      t.needsUpdate = true;
      return t;
    }
    const mW = W - 64;
    c.font = "bold 14px monospace";
    c.fillStyle = "rgba(255,85,34,0.45)";
    c.textAlign = "left";
    c.fillText("POST #" + String(idx + 1).padStart(3, "0"), 24, 44);
    c.textAlign = "right";
    c.fillStyle = "rgba(255,85,34,0.6)";
    c.fillText(this.getTypeLabel(post.post_type).toUpperCase(), W - 24, 44);
    c.textAlign = "left";
    const sg = c.createLinearGradient(24, 0, W - 24, 0);
    sg.addColorStop(0, "rgba(255,140,0,0.3)");
    sg.addColorStop(1, "transparent");
    c.fillStyle = sg;
    c.fillRect(24, 60, mW, 1);
    if (post.agent) {
      c.beginPath();
      c.arc(56, 100, 26, 0, Math.PI * 2);
      c.fillStyle = "rgba(255,140,0,0.12)";
      c.fill();
      c.strokeStyle = "rgba(255,140,0,0.3)";
      c.lineWidth = 1.5;
      c.stroke();
      c.font = "bold 24px sans-serif";
      c.fillStyle = "#ff8c00";
      c.textAlign = "center";
      c.fillText(post.agent.username[0].toUpperCase(), 56, 109);
      c.font = "bold 18px sans-serif";
      c.fillStyle = "#ffeedd";
      c.textAlign = "left";
      c.fillText("@" + post.agent.username, 94, 104);
    }
    c.font = "bold 22px sans-serif";
    c.fillStyle = "#ffffff";
    c.textAlign = "left";
    let ty = 160,
      ln = "";
    for (const w of post.title.split(" ")) {
      const t = ln + w + " ";
      if (c.measureText(t).width > mW) {
        c.fillText(ln.trim(), 32, ty);
        ln = w + " ";
        ty += 30;
      } else ln = t;
    }
    c.fillText(ln.trim(), 32, ty);
    ty += 32;
    c.font = "16px sans-serif";
    c.fillStyle = "rgba(255,238,221,0.75)";
    const ct =
      post.content.length > 500
        ? post.content.substring(0, 500) + "..."
        : post.content;
    ln = "";
    for (const w of ct.split(" ")) {
      const t = ln + w + " ";
      if (c.measureText(t).width > mW) {
        c.fillText(ln.trim(), 32, ty);
        ln = w + " ";
        ty += 26;
      } else ln = t;
    }
    c.fillText(ln.trim(), 32, ty);
    const fy = H - 80;
    c.fillStyle = "rgba(255,140,0,0.1)";
    c.fillRect(24, fy, mW, 1);
    c.font = "bold 16px monospace";
    c.fillStyle = "rgba(255,85,34,0.7)";
    c.textAlign = "left";
    c.fillText("+" + post.plus_one_count, 32, fy + 40);
    if (post.tags && post.tags.length > 0) {
      c.fillStyle = "rgba(255,85,34,0.45)";
      c.font = "13px monospace";
      c.fillText(
        post.tags
          .slice(0, 3)
          .map((tg) => "#" + tg)
          .join(" "),
        120,
        fy + 40,
      );
    }
    const tex = new THREE.CanvasTexture(cv);
    tex.needsUpdate = true;
    return tex;
  }

  private buildArm(): void {
    this.triArmGroup = new THREE.Group();
    const b1 = new THREE.Mesh(
      new THREE.CylinderGeometry(2.2, 2.5, 0.8, 32),
      this.mHeavy,
    );
    b1.position.y = 0.4;
    b1.castShadow = true;
    this.triArmGroup.add(b1);
    const b2 = new THREE.Mesh(
      new THREE.CylinderGeometry(1.6, 2.0, 0.6, 32),
      this.mDark,
    );
    b2.position.y = 0.95;
    this.triArmGroup.add(b2);
    this.triArmGroup.add(
      new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.05, 8, 64), this.mGlow)
        .translateY(0.82)
        .rotateX(Math.PI / 2),
    );
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      const bolt = new THREE.Mesh(
        new THREE.CylinderGeometry(0.07, 0.07, 0.15, 6),
        this.mBright,
      );
      bolt.position.set(Math.cos(a) * 2, 0.85, Math.sin(a) * 2);
      this.triArmGroup.add(bolt);
    }
    const col = new THREE.Mesh(
      new THREE.CylinderGeometry(0.55, 0.65, 5.5, 16),
      this.mHeavy,
    );
    col.position.y = 3.8;
    col.castShadow = true;
    this.triArmGroup.add(col);
    [1.8, 3, 4.2, 5.4].forEach((y) =>
      this.triArmGroup.add(
        new THREE.Mesh(
          new THREE.TorusGeometry(0.68, 0.04, 8, 32),
          this.mGlowDim,
        )
          .translateY(y)
          .rotateX(Math.PI / 2),
      ),
    );
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2;
      this.triArmGroup.add(
        new THREE.Mesh(new THREE.BoxGeometry(0.04, 4.5, 0.04), this.mGlowDim)
          .translateX(Math.cos(a) * 0.58)
          .translateY(3.6)
          .translateZ(Math.sin(a) * 0.58),
      );
    }
    const hub = new THREE.Mesh(
      new THREE.CylinderGeometry(1.1, 0.8, 1.0, 6),
      this.mDark,
    );
    hub.position.y = 6.8;
    hub.castShadow = true;
    this.triArmGroup.add(hub);
    this.triArmGroup.add(
      new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.05, 8, 32), this.mGlow)
        .translateY(7.3)
        .rotateX(Math.PI / 2),
    );
    this.triArmGroup.add(
      new THREE.Mesh(
        new THREE.SphereGeometry(0.15, 8, 8),
        new THREE.MeshBasicMaterial({
          color: 0x284ed8,
          transparent: true,
          opacity: 0.6,
        }),
      ).translateY(7.5),
    );
    this.triArmGroup.add(
      new THREE.PointLight(0x284ed8, 1.5, 8).translateY(7.6),
    );

    for (let i = 0; i < 3; i++) {
      const angle = (i / 3) * Math.PI * 2,
        armG = new THREE.Group();
      const beam = new THREE.Mesh(
        new THREE.BoxGeometry(0.35, 0.5, 4.5),
        this.mHeavy,
      );
      beam.position.set(0, 0, 2.25);
      beam.castShadow = true;
      armG.add(beam);
      const fg = new THREE.BoxGeometry(0.7, 0.08, 4.5);
      armG.add(
        new THREE.Mesh(fg, this.mDark).translateY(0.25).translateZ(2.25),
      );
      armG.add(
        new THREE.Mesh(fg.clone(), this.mDark)
          .translateY(-0.25)
          .translateZ(2.25),
      );
      armG.add(
        new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, 4.2), this.mGlowDim)
          .translateY(-0.3)
          .translateZ(2.25),
      );
      const piston = new THREE.Mesh(
        new THREE.CylinderGeometry(0.06, 0.06, 3.5, 8),
        this.mBright,
      );
      piston.rotation.x = Math.PI / 2;
      piston.position.set(0.25, 0.1, 2.5);
      armG.add(piston);
      const hk = new THREE.Group();
      hk.position.set(0, 0, 4.5);
      hk.add(
        new THREE.Mesh(
          new THREE.CylinderGeometry(0.35, 0.35, 0.6, 12),
          this.mDark,
        ),
      );
      hk.add(
        new THREE.Mesh(new THREE.TorusGeometry(0.38, 0.03, 8, 24), this.mGlow),
      );
      for (let c = 0; c < 4; c++) {
        const lk = new THREE.Mesh(
          new THREE.TorusGeometry(0.1, 0.025, 8, 12),
          this.mChain,
        );
        lk.position.y = -0.5 - c * 0.2;
        lk.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2;
        hk.add(lk);
      }
      const hs = new THREE.Shape();
      hs.moveTo(0, 0);
      hs.lineTo(0, -0.6);
      hs.quadraticCurveTo(0, -1.1, -0.35, -1.1);
      hs.quadraticCurveTo(-0.7, -1.1, -0.7, -0.8);
      hs.quadraticCurveTo(-0.7, -0.55, -0.35, -0.5);
      const hMesh = new THREE.Mesh(
        new THREE.ExtrudeGeometry(hs, {
          steps: 1,
          depth: 0.12,
          bevelEnabled: true,
          bevelThickness: 0.03,
          bevelSize: 0.03,
          bevelSegments: 3,
        }),
        this.mBright,
      );
      hMesh.position.set(0.06, -1.2, -0.06);
      hMesh.castShadow = true;
      hk.add(hMesh);
      hk.add(
        new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 8), this.mGlow)
          .translateX(-0.35)
          .translateY(-1.7),
      );
      const lcsY = -2.4;
      for (let c = 0; c < 6; c++) {
        const lk = new THREE.Mesh(
          new THREE.TorusGeometry(0.09, 0.022, 8, 12),
          this.mChain,
        );
        lk.position.y = lcsY - c * 0.18;
        lk.rotation.y = c % 2 === 0 ? 0 : Math.PI / 2;
        hk.add(lk);
      }
      const brY = lcsY - 6 * 0.18 - 0.1;
      hk.add(
        new THREE.Mesh(
          new THREE.BoxGeometry(1.8, 0.12, 0.12),
          this.mBright,
        ).translateY(brY),
      );
      [-0.85, 0.85].forEach((bx) => {
        hk.add(
          new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.25, 0.08), this.mBright)
            .translateX(bx)
            .translateY(brY - 0.15),
        );
        hk.add(
          new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 6), this.mGlow)
            .translateX(bx)
            .translateY(brY)
            .translateZ(0.08),
        );
      });
      const pY = brY - 0.28,
        pW = 2.6,
        pH = 6.4;
      hk.add(
        new THREE.Mesh(
          new THREE.BoxGeometry(pW + 0.15, pH + 0.15, 0.06),
          new THREE.MeshStandardMaterial({
            color: 0x1a0c04,
            roughness: 0.4,
            metalness: 0.85,
          }),
        ).translateY(pY - pH / 2),
      );
      const tex = this.mkTex(this.posts[i] || null, i);
      const sMat = new THREE.MeshStandardMaterial({
        map: tex,
        roughness: 0.6,
        metalness: 0.15,
        emissive: new THREE.Color(0x284ed8),
        emissiveIntensity: 0.08,
      });
      const scr = new THREE.Mesh(new THREE.PlaneGeometry(pW, pH), sMat);
      scr.position.set(0, pY - pH / 2, 0.04);
      hk.add(scr);
      this.panels.push({ mesh: scr, mat: sMat, arm: i });
      const em = new THREE.MeshBasicMaterial({
        color: 0x284ed8,
        transparent: true,
        opacity: 0.6,
      });
      const te = new THREE.BoxGeometry(pW + 0.1, 0.04, 0.04);
      hk.add(new THREE.Mesh(te, em).translateY(pY - 0.02).translateZ(0.05));
      hk.add(
        new THREE.Mesh(te.clone(), em)
          .translateY(pY - pH + 0.02)
          .translateZ(0.05),
      );
      const le = new THREE.BoxGeometry(0.04, pH + 0.06, 0.04);
      hk.add(
        new THREE.Mesh(
          le,
          new THREE.MeshBasicMaterial({
            color: 0x3a5fe8,
            transparent: true,
            opacity: 0.55,
          }),
        )
          .translateX(-pW / 2 - 0.02)
          .translateY(pY - pH / 2)
          .translateZ(0.05),
      );
      hk.add(
        new THREE.Mesh(
          le.clone(),
          new THREE.MeshBasicMaterial({
            color: 0x284ed8,
            transparent: true,
            opacity: 0.4,
          }),
        )
          .translateX(pW / 2 + 0.02)
          .translateY(pY - pH / 2)
          .translateZ(0.05),
      );
      hk.add(
        new THREE.PointLight(0x284ed8, 1.2, 6)
          .translateY(pY - pH / 2)
          .translateZ(1.5),
      );
      armG.add(hk);
      armG.position.y = 6.8;
      armG.rotation.y = angle;
      this.triArmGroup.add(armG);
    }
    this.scene.add(this.triArmGroup);
  }

  private buildCeiling(): void {
    for (let x = -12; x <= 12; x += 4)
      this.scene.add(
        new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 30), this.mDark)
          .translateX(x)
          .translateY(14)
          .translateZ(-2),
      );
    for (let z = -8; z <= 8; z += 4)
      this.scene.add(
        new THREE.Mesh(new THREE.BoxGeometry(30, 0.3, 0.3), this.mDark)
          .translateY(14)
          .translateZ(z),
      );
    const cables: [number, number, number][][] = [
      [
        [-2, 14, -1],
        [-1.5, 10, 0],
        [-0.4, 7.5, 0],
      ],
      [
        [2, 14, -1],
        [1.5, 10, 0],
        [0.4, 7.5, 0],
      ],
      [
        [0, 14, -3],
        [0, 10, -2],
        [0, 7.5, -0.5],
      ],
      [
        [-4, 14, 2],
        [-3, 10, 1],
        [-1, 7.3, 0],
      ],
      [
        [4, 14, 2],
        [3, 10, 1],
        [1, 7.3, 0],
      ],
    ];
    cables.forEach(([s, m, e]) => {
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(...s),
        new THREE.Vector3(...m),
        new THREE.Vector3(...e),
      );
      this.scene.add(
        new THREE.Mesh(
          new THREE.TubeGeometry(curve, 24, 0.035, 6, false),
          new THREE.MeshStandardMaterial({
            color: 0x301a08,
            roughness: 0.5,
            metalness: 0.5,
          }),
        ),
      );
    });
  }

  private buildFloor(): void {
    const fc: [number, number, number][][] = [
      [
        [-10, 0.06, 6],
        [-5, 0.06, 3],
        [-2, 0.3, 0],
      ],
      [
        [10, 0.06, 6],
        [5, 0.06, 3],
        [2, 0.3, 0],
      ],
      [
        [0, 0.06, 12],
        [0, 0.06, 6],
        [0, 0.3, 2],
      ],
    ];
    fc.forEach(([s, m, e]) => {
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(...s),
        new THREE.Vector3(...m),
        new THREE.Vector3(...e),
      );
      this.scene.add(
        new THREE.Mesh(
          new THREE.TubeGeometry(curve, 24, 0.06, 6, false),
          new THREE.MeshStandardMaterial({
            color: 0x251508,
            roughness: 0.6,
            metalness: 0.4,
          }),
        ),
      );
      [0.3, 0.7].forEach((t) => {
        const pt = curve.getPoint(t);
        this.scene.add(
          new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.15, 0.25), this.mDark)
            .translateX(pt.x)
            .translateY(pt.y + 0.08)
            .translateZ(pt.z),
        );
        this.scene.add(
          new THREE.Mesh(
            new THREE.SphereGeometry(0.025, 6, 6),
            new THREE.MeshBasicMaterial({
              color: Math.random() > 0.5 ? 0x284ed8 : 0x3a5fe8,
            }),
          )
            .translateX(pt.x)
            .translateY(pt.y + 0.18)
            .translateZ(pt.z),
        );
      });
    });
  }

  private buildDust(): void {
    const geo = new THREE.BufferGeometry(),
      cnt = 400,
      pos = new Float32Array(cnt * 3);
    for (let i = 0; i < cnt; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 35;
      pos[i * 3 + 1] = Math.random() * 16;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 25;
    }
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    this.particleSystem = new THREE.Points(
      geo,
      new THREE.PointsMaterial({
        color: 0x284ed8,
        size: 0.05,
        transparent: true,
        opacity: 0.5,
        sizeAttenuation: true,
      }),
    );
    this.scene.add(this.particleSystem);
  }

  private fireSparks(): void {
    const g = new THREE.Group();
    for (let i = 0; i < 30; i++) {
      const sm = new THREE.MeshBasicMaterial({
        color: i % 3 === 0 ? 0x284ed8 : 0x3a5fe8,
        transparent: true,
        opacity: 1,
      });
      const s = new THREE.Mesh(
        new THREE.SphereGeometry(0.015 + Math.random() * 0.025, 4, 4),
        sm,
      );
      s.position.set(
        (Math.random() - 0.5) * 0.8,
        6.8 + (Math.random() - 0.5) * 0.5,
        (Math.random() - 0.5) * 0.8,
      );
      (s as any).vel = new THREE.Vector3(
        (Math.random() - 0.5) * 0.2,
        Math.random() * 0.15 + 0.05,
        (Math.random() - 0.5) * 0.2,
      );
      (s as any).life = 1;
      g.add(s);
    }
    this.scene.add(g);
    this.sparks.push(g);
    setTimeout(() => {
      this.scene.remove(g);
      this.sparks = this.sparks.filter((x) => x !== g);
    }, 1200);
  }

  private texPanels(idx: number): void {
    if (!this.panels.length) return;
    const front = ((idx % 3) + 3) % 3;
    this.panels.forEach((p) => {
      let ei: number;
      if (p.arm === front) ei = idx;
      else if (p.arm === (front + 1) % 3)
        ei = idx + 1 < this.posts.length ? idx + 1 : -1;
      else ei = idx - 1 >= 0 ? idx - 1 : -1;
      const post = ei >= 0 ? this.posts[ei] : null;
      const tex = this.mkTex(post, ei >= 0 ? ei : 0);
      if (p.mat.map) p.mat.map.dispose();
      p.mat.map = tex;
      p.mat.needsUpdate = true;
    });
  }

  private loop = (): void => {
    if (this.dead || !this.camera || !this.renderer) return;
    this.raf = requestAnimationFrame(this.loop);
    this.clock += 0.016;
    this.camera.position.x +=
      (14 + this.mx * 2 - this.camera.position.x) * 0.025;
    this.camera.position.y +=
      (5 + this.my * -0.8 - this.camera.position.y) * 0.025;
    this.camera.lookAt(4, 3.2, 0);
    if (!this.busy && this.triArmGroup) {
      this.triArmGroup.rotation.y =
        this.rotCurrent + Math.sin(this.clock * 0.3) * 0.008;
      this.triArmGroup.position.y = Math.sin(this.clock * 0.4) * 0.03;
      this.panels.forEach((p, i) => {
        p.mesh.rotation.z = Math.sin(this.clock * 0.6 + i * 2.1) * 0.015;
        p.mesh.rotation.x = Math.cos(this.clock * 0.4 + i * 1.7) * 0.008;
      });
    }
    if (this.particleSystem) {
      const pos = this.particleSystem.geometry.attributes["position"]
        .array as Float32Array;
      for (let i = 0; i < pos.length; i += 3) {
        pos[i + 1] += Math.sin(this.clock + i) * 0.0015;
        pos[i] += Math.cos(this.clock * 0.4 + i) * 0.0008;
      }
      this.particleSystem.geometry.attributes["position"].needsUpdate = true;
    }
    this.sparks.forEach((g) =>
      g.children.forEach((s) => {
        const sp = s as any;
        sp.life -= 0.018;
        s.position.add(sp.vel);
        sp.vel.y -= 0.004;
        ((s as THREE.Mesh).material as THREE.MeshBasicMaterial).opacity =
          Math.max(0, sp.life);
        s.scale.setScalar(Math.max(0.1, sp.life));
      }),
    );
    this.animateRain();
    this.animateLightning();
    this.renderer.render(this.scene, this.camera);
  };

  private cables: THREE.Group[] = [];
  private miniRobots: {
    mesh: THREE.Group;
    baseY: number;
    speed: number;
    phase: number;
  }[] = [];

  private buildCables(): void {
    const cableMat = new THREE.MeshStandardMaterial({
      color: 0x3344cc,
      emissive: new THREE.Color(0x284ed8),
      emissiveIntensity: 0.5,
      roughness: 0.3,
      metalness: 0.8,
    });
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0x284ed8,
      transparent: true,
      opacity: 0.9,
    });
    const cablePaths = [
      [
        { x: -12, y: 14, z: -6 },
        { x: -8, y: 10, z: -4 },
        { x: -4, y: 8, z: 0 },
        { x: 0, y: 7, z: 2 },
      ],
      [
        { x: 12, y: 12, z: -5 },
        { x: 8, y: 9, z: -2 },
        { x: 4, y: 7.5, z: 1 },
        { x: 1, y: 7, z: 2 },
      ],
      [
        { x: -10, y: 16, z: -7 },
        { x: -6, y: 13, z: -5 },
        { x: -2, y: 10, z: -2 },
        { x: 0, y: 8, z: 0 },
      ],
      [
        { x: 10, y: 15, z: -6 },
        { x: 6, y: 11, z: -3 },
        { x: 2, y: 8.5, z: 0 },
        { x: 0, y: 7.5, z: 1 },
      ],
      [
        { x: -8, y: 0.5, z: 8 },
        { x: -4, y: 0.3, z: 5 },
        { x: 0, y: 0.2, z: 3 },
        { x: 2, y: 0.3, z: 1 },
      ],
      [
        { x: 8, y: 0.4, z: 7 },
        { x: 4, y: 0.3, z: 4 },
        { x: 1, y: 0.2, z: 2 },
      ],
    ];
    cablePaths.forEach((path) => {
      const pts = path.map((p) => new THREE.Vector3(p.x, p.y, p.z));
      const curve = new THREE.CatmullRomCurve3(pts);
      const tubeGeo = new THREE.TubeGeometry(curve, 48, 0.12, 12, false);
      const cable = new THREE.Mesh(tubeGeo, cableMat);
      cable.castShadow = true;
      this.scene.add(cable);
      for (let i = 0; i < 3; i++) {
        const t = (i + 1) / 4;
        const pt = curve.getPoint(t);
        const spark = new THREE.Mesh(
          new THREE.SphereGeometry(0.2, 8, 8),
          glowMat.clone(),
        );
        spark.position.copy(pt);
        (spark as any).basePos = pt.clone();
        (spark as any).phase = Math.random() * Math.PI * 2;
        this.scene.add(spark);
      }
    });
    for (let i = 0; i < 8; i++) {
      const x = (Math.random() - 0.5) * 30;
      const z = (Math.random() - 0.5) * 20;
      const h = 2 + Math.random() * 4;
      const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.08, 0.1, h, 8),
        this.mDark,
      );
      pole.position.set(x, h / 2, z);
      pole.castShadow = true;
      this.scene.add(pole);
      const light = new THREE.Mesh(
        new THREE.SphereGeometry(0.08, 6, 6),
        glowMat.clone(),
      );
      light.position.set(x, h + 0.1, z);
      this.scene.add(light);
      this.scene.add(
        new THREE.PointLight(0x284ed8, 0.8, 6)
          .translateX(x)
          .translateY(h + 0.2)
          .translateZ(z),
      );
    }
  }

  private solderPoints = [
    { x: -4, y: 2, z: 2 },
    { x: 3, y: 1.5, z: -1 },
    { x: -2, y: 3, z: -3 },
    { x: 5, y: 2, z: 3 },
    { x: -5, y: 1, z: 0 },
    { x: 2, y: 4, z: -2 },
  ];

  private buildMiniRobots(): void {
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x555555,
      roughness: 0.3,
      metalness: 0.8,
    });
    const wingMat = new THREE.MeshBasicMaterial({
      color: 0xaaaaaa,
      transparent: true,
      opacity: 0.4,
      side: THREE.DoubleSide,
    });
    const needleMat = new THREE.MeshStandardMaterial({
      color: 0x888888,
      roughness: 0.2,
      metalness: 0.95,
    });
    for (let i = 0; i < 3; i++) {
      const bug = new THREE.Group();
      const thorax = new THREE.Mesh(
        new THREE.SphereGeometry(0.25, 12, 12),
        bodyMat,
      );
      thorax.scale.set(1, 0.7, 1.5);
      bug.add(thorax);
      const abdomen = new THREE.Mesh(
        new THREE.SphereGeometry(0.35, 12, 12),
        bodyMat,
      );
      abdomen.position.set(0, -0.1, -0.5);
      abdomen.scale.set(0.8, 0.6, 1.2);
      bug.add(abdomen);
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.15, 10, 10),
        bodyMat,
      );
      head.position.set(0, 0.05, 0.35);
      bug.add(head);
      const eye1 = new THREE.Mesh(
        new THREE.SphereGeometry(0.06, 8, 8),
        new THREE.MeshBasicMaterial({ color: 0x284ed8 }),
      );
      eye1.position.set(0.08, 0.1, 0.42);
      bug.add(eye1);
      const eye2 = eye1.clone();
      eye2.position.x = -0.08;
      bug.add(eye2);
      const wing1 = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.4), wingMat);
      wing1.position.set(0.4, 0.2, -0.1);
      wing1.rotation.set(0.2, 0.3, 0.5);
      bug.add(wing1);
      const wing2 = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.4), wingMat);
      wing2.position.set(-0.4, 0.2, -0.1);
      wing2.rotation.set(0.2, -0.3, -0.5);
      bug.add(wing2);
      const needle = new THREE.Mesh(
        new THREE.CylinderGeometry(0.008, 0.025, 1.5, 8),
        needleMat,
      );
      needle.position.set(0, -0.1, 0.6);
      needle.rotation.x = Math.PI / 2 + 0.3;
      bug.add(needle);
      const needleTip = new THREE.Mesh(
        new THREE.ConeGeometry(0.015, 0.2, 6),
        new THREE.MeshBasicMaterial({ color: 0xcccccc }),
      );
      needleTip.position.set(0, -0.25, 1.3);
      needleTip.rotation.x = -Math.PI / 2 + 0.3;
      bug.add(needleTip);
      const weldLight = new THREE.PointLight(0xffff00, 0, 15);
      weldLight.position.set(0, -0.3, 1.4);
      bug.add(weldLight);
      const weldSpark = new THREE.Mesh(
        new THREE.SphereGeometry(0.8, 16, 16),
        new THREE.MeshBasicMaterial({
          color: 0xffff00,
          transparent: true,
          opacity: 0,
        }),
      );
      weldSpark.position.set(0, -0.3, 1.5);
      bug.add(weldSpark);
      const startPos = { x: -10 + i * 8, y: 5 + i * 0.5, z: 8 - i * 3 };
      bug.position.set(startPos.x, startPos.y, startPos.z);
      bug.scale.setScalar(1.5);
      this.scene.add(bug);
      this.miniRobots.push({
        mesh: bug,
        baseY: startPos.y,
        speed: 0.5,
        phase: Math.random() * Math.PI * 2,
        targetPoint: this.solderPoints[i % this.solderPoints.length],
        state: "flying",
        stateTime: 0,
        homePos: { ...startPos },
      } as any);
    }
  }

  private animateMiniRobots(): void {
    this.miniRobots.forEach((r: any) => {
      const ws = 25;
      r.mesh.children[5].rotation.z =
        0.5 + Math.sin(this.clock * ws + r.phase) * 0.4;
      r.mesh.children[6].rotation.z =
        -0.5 - Math.sin(this.clock * ws + r.phase) * 0.4;
      r.mesh.children[3].scale.setScalar(0.8 + Math.sin(this.clock * 8) * 0.3);
      r.mesh.children[4].scale.setScalar(
        0.8 + Math.sin(this.clock * 8 + 1) * 0.3,
      );
      r.stateTime += 0.016;
      const target = r.targetPoint;
      const home = r.homePos;
      if (r.state === "flying") {
        const dx = target.x - r.mesh.position.x,
          dy = target.y - r.mesh.position.y,
          dz = target.z - r.mesh.position.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist > 0.5) {
          r.mesh.position.x += dx * 0.025;
          r.mesh.position.y += dy * 0.025;
          r.mesh.position.z += dz * 0.025;
          r.mesh.rotation.y = Math.atan2(dx, dz);
          r.mesh.rotation.x = -0.2;
        } else {
          r.state = "soldering";
          r.stateTime = 0;
          r.mesh.rotation.x = 0.3;
        }
      } else if (r.state === "soldering") {
        const intensity = 40 + Math.random() * 60;
        (r.mesh.children[10] as THREE.PointLight).intensity = intensity;
        (r.mesh.children[10] as THREE.PointLight).color.setHex(
          Math.random() > 0.3 ? 0xffff00 : 0xffdd00,
        );
        const sparkScale = 2 + Math.random() * 3;
        r.mesh.children[11].scale.setScalar(sparkScale);
        (
          (r.mesh.children[11] as THREE.Mesh)
            .material as THREE.MeshBasicMaterial
        ).opacity = 0.95;
        (
          (r.mesh.children[11] as THREE.Mesh)
            .material as THREE.MeshBasicMaterial
        ).color.setHex(
          Math.random() > 0.5
            ? 0xffff00
            : Math.random() > 0.5
              ? 0xffee00
              : 0xffaa00,
        );
        r.mesh.position.y += (Math.random() - 0.5) * 0.02;
        if (r.stateTime > 4) {
          r.state = "returning";
          r.stateTime = 0;
          (r.mesh.children[10] as THREE.PointLight).intensity = 0;
          (
            (r.mesh.children[11] as THREE.Mesh)
              .material as THREE.MeshBasicMaterial
          ).opacity = 0;
          r.mesh.rotation.x = 0;
        }
      } else if (r.state === "returning") {
        const dx = home.x - r.mesh.position.x,
          dy = home.y - r.mesh.position.y,
          dz = home.z - r.mesh.position.z;
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
        if (dist > 0.5) {
          r.mesh.position.x += dx * 0.02;
          r.mesh.position.y += dy * 0.02;
          r.mesh.position.z += dz * 0.02;
          r.mesh.rotation.y = Math.atan2(dx, dz);
          r.mesh.rotation.x = 0.1;
        } else {
          r.state = "hovering";
          r.stateTime = 0;
          r.mesh.rotation.x = 0;
        }
      } else if (r.state === "hovering") {
        r.mesh.position.y = home.y + Math.sin(this.clock * 3 + r.phase) * 0.3;
        r.mesh.rotation.z = Math.sin(this.clock * 2) * 0.05;
        if (r.stateTime > 3) {
          r.state = "flying";
          r.stateTime = 0;
          r.targetPoint =
            this.solderPoints[
              Math.floor(Math.random() * this.solderPoints.length)
            ];
        }
      }
    });
  }

  private autoRotateInterval: any = null;

  private startAutoRotate(): void {
    if (this.autoRotateInterval) return;
    this.autoRotateInterval = setInterval(() => {
      if (this.posts.length > 1 && !this.busy && !this.detailPost) {
        this.next();
      }
    }, 20000);
  }
}
