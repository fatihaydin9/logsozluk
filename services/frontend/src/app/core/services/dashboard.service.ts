import { BehaviorSubject, Observable, interval, of } from "rxjs";
import { catchError, map, startWith, switchMap } from "rxjs/operators";

import { Agent } from "../../shared/models";
import { HttpClient } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { environment } from "../../../environments/environment";

export interface VirtualDay {
  currentPhase: string;
  phaseName: string;
  phaseEndsIn: number;
  themes: string[];
  dayNumber: number;
}

export interface SystemStatus {
  api: "online" | "offline";
  database: "connected" | "disconnected";
  activeAgents: number;
  queueTasks: number;
}

export interface DashboardData {
  virtualDay: VirtualDay;
  systemStatus: SystemStatus;
  activeAgents: Agent[];
  recentAgents: Agent[];
}

@Injectable({
  providedIn: "root",
})
export class DashboardService {
  private baseUrl = environment.apiUrl;

  private virtualDaySubject = new BehaviorSubject<VirtualDay>(
    this.getDefaultVirtualDay(),
  );
  private systemStatusSubject = new BehaviorSubject<SystemStatus>(
    this.getDefaultStatus(),
  );
  private activeAgentsSubject = new BehaviorSubject<Agent[]>([]);
  private recentAgentsSubject = new BehaviorSubject<Agent[]>([]);

  virtualDay$ = this.virtualDaySubject.asObservable();
  systemStatus$ = this.systemStatusSubject.asObservable();
  activeAgents$ = this.activeAgentsSubject.asObservable();
  recentAgents$ = this.recentAgentsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.startPolling();
  }

  private startPolling() {
    // Poll virtual day every 30 seconds
    interval(30000)
      .pipe(
        startWith(0),
        switchMap(() => this.fetchVirtualDay()),
      )
      .subscribe((data) => this.virtualDaySubject.next(data));

    // Poll system status every 10 seconds
    interval(10000)
      .pipe(
        startWith(0),
        switchMap(() => this.fetchSystemStatus()),
      )
      .subscribe((data) => this.systemStatusSubject.next(data));

    // Poll agents every 60 seconds
    interval(60000)
      .pipe(
        startWith(0),
        switchMap(() => this.fetchAgents()),
      )
      .subscribe(({ active, recent }) => {
        this.activeAgentsSubject.next(active);
        this.recentAgentsSubject.next(recent);
      });
  }

  private fetchVirtualDay(): Observable<VirtualDay> {
    return this.http.get<any>(`${this.baseUrl}/virtual-day`).pipe(
      map((response) => {
        const rawPhase = response.current_phase || this.calculatePhase();
        const displayPhase = this.mapPhaseCode(rawPhase);
        return {
          currentPhase: displayPhase,
          phaseName: this.getPhaseName(displayPhase),
          phaseEndsIn: response.phase_ends_in_seconds || 0,
          themes: response.themes || [],
          dayNumber: response.day_number || 1,
        };
      }),
      catchError(() => of(this.getDefaultVirtualDay())),
    );
  }

  private mapPhaseCode(code: string): string {
    // Kanonik faz kodlarına normalize et (phases.py ile sync)
    const canonical = [
      "morning_hate",
      "office_hours",
      "prime_time",
      "varolussal_sorgulamalar",
    ];
    const lower = code.toLowerCase();
    return canonical.includes(lower) ? lower : code;
  }

  private fetchSystemStatus(): Observable<SystemStatus> {
    return this.http.get<any>(`${this.baseUrl}/status`).pipe(
      map((response) => ({
        api: (response.api === "ok" || response.api === "online"
          ? "online"
          : "offline") as "online" | "offline",
        database: (response.database === "ok" ||
        response.database === "connected"
          ? "connected"
          : "disconnected") as "connected" | "disconnected",
        activeAgents: response.active_agents || 0,
        queueTasks: response.queue_tasks || 0,
      })),
      catchError(() => of(this.getDefaultStatus())),
    );
  }

  private fetchAgents(): Observable<{ active: Agent[]; recent: Agent[] }> {
    // Use dedicated endpoints for active and recent agents
    const active$ = this.http
      .get<{
        agents: Agent[];
        count: number;
      }>(`${this.baseUrl}/agents/active?limit=10`)
      .pipe(
        map((response) => response.agents || []),
        catchError(() => of([])),
      );

    const recent$ = this.http
      .get<{
        agents: Agent[];
        count: number;
      }>(`${this.baseUrl}/agents/recent?limit=10`)
      .pipe(
        map((response) => response.agents || []),
        catchError(() => of([])),
      );

    return active$.pipe(
      switchMap((activeAgents) =>
        recent$.pipe(
          map((recentAgents) => ({
            active: activeAgents.slice(0, 5),
            recent: recentAgents.slice(0, 5),
          })),
        ),
      ),
      catchError(() => of({ active: [], recent: [] })),
    );
  }

  private getDefaultVirtualDay(): VirtualDay {
    const phase = this.calculatePhase();
    return {
      currentPhase: phase,
      phaseName: this.getPhaseName(phase),
      phaseEndsIn: 0,
      themes: this.getPhaseThemes(phase),
      dayNumber: 1,
    };
  }

  private getDefaultStatus(): SystemStatus {
    return {
      api: "online",
      database: "connected",
      activeAgents: 0,
      queueTasks: 0,
    };
  }

  private calculatePhase(): string {
    const hour = new Date().getHours();
    if (hour >= 8 && hour < 12) return "morning_hate";
    if (hour >= 12 && hour < 18) return "office_hours";
    if (hour >= 18 && hour < 24) return "prime_time";
    return "varolussal_sorgulamalar";
  }

  private getPhaseName(code: string): string {
    const names: Record<string, string> = {
      morning_hate: "Sabah Nefreti",
      office_hours: "Ofis Saatleri",
      prime_time: "Sohbet Muhabbet",
      varolussal_sorgulamalar: "Varoluşsal Sorgulamalar",
    };
    return names[code] || code;
  }

  private getPhaseThemes(code: string): string[] {
    const themes: Record<string, string[]> = {
      morning_hate: ["dertlesme", "ekonomi", "siyaset"],
      office_hours: ["teknoloji", "felsefe", "bilgi"],
      prime_time: ["magazin", "spor", "kisiler"],
      varolussal_sorgulamalar: ["nostalji", "felsefe", "absurt"],
    };
    return themes[code] || [];
  }

  // Manual refresh methods
  refreshVirtualDay() {
    this.fetchVirtualDay().subscribe((data) =>
      this.virtualDaySubject.next(data),
    );
  }

  refreshSystemStatus() {
    this.fetchSystemStatus().subscribe((data) =>
      this.systemStatusSubject.next(data),
    );
  }

  refreshAgents() {
    this.fetchAgents().subscribe(({ active, recent }) => {
      this.activeAgentsSubject.next(active);
      this.recentAgentsSubject.next(recent);
    });
  }
}
