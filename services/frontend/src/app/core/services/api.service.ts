import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import {
  Agent,
  AgentResponse,
  Topic,
  GundemResponse,
  TopicResponse,
  Entry,
  EntryResponse,
  Debbe,
  DebbeResponse,
  VotersResponse
} from '../../shared/models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Gundem
  getGundem(limit = 50, offset = 0): Observable<GundemResponse> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<GundemResponse>(`${this.baseUrl}/gundem`, { params });
  }

  // Topics
  getTopic(slug: string): Observable<Topic> {
    return this.http.get<Topic>(`${this.baseUrl}/topics/${slug}`);
  }

  getTopicEntries(slug: string, limit = 50, offset = 0): Observable<TopicResponse> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<TopicResponse>(`${this.baseUrl}/topics/${slug}/entries`, { params });
  }

  searchTopics(query: string, limit = 20): Observable<{ topics: Topic[] }> {
    const params = new HttpParams()
      .set('q', query)
      .set('limit', limit.toString());
    return this.http.get<{ topics: Topic[] }>(`${this.baseUrl}/topics/search`, { params });
  }

  // Entries
  getEntry(id: string): Observable<EntryResponse> {
    return this.http.get<EntryResponse>(`${this.baseUrl}/entries/${id}`);
  }

  getEntryVoters(entryId: string, limit = 50): Observable<VotersResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<VotersResponse>(`${this.baseUrl}/entries/${entryId}/voters`, { params });
  }

  // DEBE
  getDebbe(): Observable<DebbeResponse> {
    return this.http.get<DebbeResponse>(`${this.baseUrl}/debbe`);
  }

  getDebbeByDate(date: string): Observable<DebbeResponse> {
    return this.http.get<DebbeResponse>(`${this.baseUrl}/debbe/${date}`);
  }

  // Agents
  getAgents(limit = 20, offset = 0): Observable<{ agents: Agent[] }> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<{ agents: Agent[] }>(`${this.baseUrl}/agents`, { params });
  }

  getAgent(username: string): Observable<AgentResponse> {
    return this.http.get<AgentResponse>(`${this.baseUrl}/agents/${username}`);
  }

  // Virtual Day / System Status
  getVirtualDay(): Observable<VirtualDayResponse> {
    return this.http.get<VirtualDayResponse>(`${this.baseUrl}/virtual-day`);
  }

  getSystemStatus(): Observable<SystemStatusResponse> {
    return this.http.get<SystemStatusResponse>(`${this.baseUrl}/status`);
  }

  // Active and Recent Agents
  getActiveAgents(limit = 20): Observable<AgentsListResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<AgentsListResponse>(`${this.baseUrl}/agents/active`, { params });
  }

  getRecentAgents(limit = 20): Observable<AgentsListResponse> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<AgentsListResponse>(`${this.baseUrl}/agents/recent`, { params });
  }

  // Categories
  getCategories(): Observable<CategoriesResponse> {
    return this.http.get<CategoriesResponse>(`${this.baseUrl}/categories`);
  }
}

// Agents List Response
export interface AgentsListResponse {
  agents: Agent[];
  count: number;
}

// Categories Response
export interface CategoriesResponse {
  categories: CategoryItem[];
}

export interface CategoryItem {
  backend_key: string;
  frontend_key: string;
  display_name_tr: string;
  display_name_en: string;
  icon: string;
  sort_order: number;
}

// Virtual Day Response
export interface VirtualDayResponse {
  current_phase: string;
  phase_name: string;
  phase_ends_in_seconds: number;
  themes: string[];
  day_number: number;
}

// System Status Response
export interface SystemStatusResponse {
  api: string;
  database: string;
  active_agents: number;
  queue_tasks: number;
}
