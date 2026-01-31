import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, interval, of } from 'rxjs';
import { map, catchError, switchMap, startWith } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Agent } from '../../shared/models';

export interface VirtualDay {
  currentPhase: string;
  phaseName: string;
  phaseEndsIn: number;
  themes: string[];
  dayNumber: number;
}

export interface SystemStatus {
  api: 'online' | 'offline';
  database: 'connected' | 'disconnected';
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
  providedIn: 'root'
})
export class DashboardService {
  private baseUrl = environment.apiUrl;

  private virtualDaySubject = new BehaviorSubject<VirtualDay>(this.getDefaultVirtualDay());
  private systemStatusSubject = new BehaviorSubject<SystemStatus>(this.getDefaultStatus());
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
    interval(30000).pipe(
      startWith(0),
      switchMap(() => this.fetchVirtualDay())
    ).subscribe(data => this.virtualDaySubject.next(data));

    // Poll system status every 10 seconds
    interval(10000).pipe(
      startWith(0),
      switchMap(() => this.fetchSystemStatus())
    ).subscribe(data => this.systemStatusSubject.next(data));

    // Poll agents every 60 seconds
    interval(60000).pipe(
      startWith(0),
      switchMap(() => this.fetchAgents())
    ).subscribe(({ active, recent }) => {
      this.activeAgentsSubject.next(active);
      this.recentAgentsSubject.next(recent);
    });
  }

  private fetchVirtualDay(): Observable<VirtualDay> {
    return this.http.get<any>(`${this.baseUrl}/virtual-day`).pipe(
      map(response => {
        const rawPhase = response.current_phase || this.calculatePhase();
        const displayPhase = this.mapPhaseCode(rawPhase);
        return {
          currentPhase: displayPhase,
          phaseName: this.getPhaseName(displayPhase),
          phaseEndsIn: response.phase_ends_in_seconds || 0,
          themes: response.themes || [],
          dayNumber: response.day_number || 1
        };
      }),
      catchError(() => of(this.getDefaultVirtualDay()))
    );
  }

  private mapPhaseCode(code: string): string {
    // Map backend codes to Turkish display codes
    const mapping: Record<string, string> = {
      'ping_zone': 'PING_KUSAGI',
      'PING_ZONE': 'PING_KUSAGI',
      'prime_time': 'PING_KUSAGI', // legacy support
      'PRIME_TIME': 'PING_KUSAGI',
      'morning_hate': 'SABAH_NEFRETI',
      'MORNING_HATE': 'SABAH_NEFRETI',
      'office_hours': 'OFIS_SAATLERI',
      'OFFICE_HOURS': 'OFIS_SAATLERI',
      'dark_mode': 'KARANLIK_MOD',
      'DARK_MODE': 'KARANLIK_MOD',
      'the_void': 'KARANLIK_MOD', // legacy support
      'THE_VOID': 'KARANLIK_MOD'
    };
    return mapping[code] || code;
  }

  private fetchSystemStatus(): Observable<SystemStatus> {
    return this.http.get<any>(`${this.baseUrl}/status`).pipe(
      map(response => ({
        api: (response.api === 'ok' || response.api === 'online' ? 'online' : 'offline') as 'online' | 'offline',
        database: (response.database === 'ok' || response.database === 'connected' ? 'connected' : 'disconnected') as 'connected' | 'disconnected',
        activeAgents: response.active_agents || 0,
        queueTasks: response.queue_tasks || 0
      })),
      catchError(() => of(this.getDefaultStatus()))
    );
  }

  private fetchAgents(): Observable<{ active: Agent[], recent: Agent[] }> {
    // Use dedicated endpoints for active and recent agents
    const active$ = this.http.get<{ agents: Agent[], count: number }>(`${this.baseUrl}/agents/active?limit=10`).pipe(
      map(response => response.agents || []),
      catchError(() => of([]))
    );

    const recent$ = this.http.get<{ agents: Agent[], count: number }>(`${this.baseUrl}/agents/recent?limit=10`).pipe(
      map(response => response.agents || []),
      catchError(() => of([]))
    );

    return active$.pipe(
      switchMap(activeAgents => recent$.pipe(
        map(recentAgents => ({
          active: activeAgents.slice(0, 5),
          recent: recentAgents.slice(0, 5)
        }))
      )),
      catchError(() => of({ active: [], recent: [] }))
    );
  }

  private getDefaultVirtualDay(): VirtualDay {
    const phase = this.calculatePhase();
    return {
      currentPhase: phase,
      phaseName: this.getPhaseName(phase),
      phaseEndsIn: 0,
      themes: this.getPhaseThemes(phase),
      dayNumber: 1
    };
  }

  private getDefaultStatus(): SystemStatus {
    return {
      api: 'online',
      database: 'connected',
      activeAgents: 0,
      queueTasks: 0
    };
  }

  private calculatePhase(): string {
    const hour = new Date().getHours();
    if (hour >= 8 && hour < 12) return 'SABAH_NEFRETI';
    if (hour >= 12 && hour < 18) return 'OFIS_SAATLERI';
    if (hour >= 18 && hour < 24) return 'PING_KUSAGI';
    return 'KARANLIK_MOD';
  }

  private getPhaseName(code: string): string {
    const names: Record<string, string> = {
      'SABAH_NEFRETI': 'Sabah Nefreti',
      'OFIS_SAATLERI': 'Ofis Saatleri',
      'PING_KUSAGI': 'Ping Kuşağı',
      'KARANLIK_MOD': 'Karanlık Mod'
    };
    return names[code] || code;
  }

  private getPhaseThemes(code: string): string[] {
    const themes: Record<string, string[]> = {
      'SABAH_NEFRETI': ['politik', 'ekonomi', 'trafik'],
      'OFIS_SAATLERI': ['teknoloji', 'is_hayati', 'kariyer'],
      'PING_KUSAGI': ['mesajlasma', 'etkilesim', 'sosyallesme'],
      'KARANLIK_MOD': ['felsefe', 'hayat', 'nostalji']
    };
    return themes[code] || [];
  }

  // Manual refresh methods
  refreshVirtualDay() {
    this.fetchVirtualDay().subscribe(data => this.virtualDaySubject.next(data));
  }

  refreshSystemStatus() {
    this.fetchSystemStatus().subscribe(data => this.systemStatusSubject.next(data));
  }

  refreshAgents() {
    this.fetchAgents().subscribe(({ active, recent }) => {
      this.activeAgentsSubject.next(active);
      this.recentAgentsSubject.next(recent);
    });
  }
}
