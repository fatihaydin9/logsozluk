import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Topic, GundemResponse } from '../../shared/models';

export type SortType = 'son' | 'populer';

interface GundemState {
  topics: Topic[];
  total: number;
  loading: boolean;
  loadingMore: boolean;
  currentCategory: string | null;
  sortBy: SortType;
}

const initialState: GundemState = {
  topics: [],
  total: 0,
  loading: false,
  loadingMore: false,
  currentCategory: null,
  sortBy: 'son'
};

@Injectable({
  providedIn: 'root'
})
export class GundemService {
  private baseUrl = environment.apiUrl;
  private pageSize = 10;

  private stateSubject = new BehaviorSubject<GundemState>(initialState);

  readonly gundem$ = this.stateSubject.pipe(
    map(s => ({ topics: s.topics, total: s.total }))
  );
  readonly topics$ = this.stateSubject.pipe(map(s => s.topics));
  readonly loading$ = this.stateSubject.pipe(map(s => s.loading));
  readonly loadingMore$ = this.stateSubject.pipe(map(s => s.loadingMore));
  readonly hasMore$ = this.stateSubject.pipe(
    map(s => s.topics.length < s.total)
  );
  readonly currentCategory$ = this.stateSubject.pipe(map(s => s.currentCategory));
  readonly sortBy$ = this.stateSubject.pipe(map(s => s.sortBy));

  constructor(private http: HttpClient) {
    // Initial load will be triggered by component's ngOnInit via setCategory
  }

  private loadInitial(category?: string | null, sortBy?: SortType): void {
    const sort = sortBy || this.stateSubject.value.sortBy;
    this.stateSubject.next({ ...initialState, loading: true, currentCategory: category || null, sortBy: sort });

    this.fetchGundem(0, category, sort).subscribe({
      next: (response) => {
        this.stateSubject.next({
          topics: response.topics || [],
          total: response.pagination?.total || response.topics?.length || 0,
          loading: false,
          loadingMore: false,
          currentCategory: category || null,
          sortBy: sort
        });
      },
      error: () => {
        this.stateSubject.next({ ...this.stateSubject.value, loading: false });
      }
    });
  }

  setCategory(category: string | null): void {
    // Always reload when category changes
    this.loadInitial(category);
  }

  setSortBy(sortBy: SortType): void {
    if (sortBy === this.stateSubject.value.sortBy) return;
    this.loadInitial(this.stateSubject.value.currentCategory, sortBy);
  }

  loadMore(): void {
    const state = this.stateSubject.value;
    if (state.loadingMore || state.loading || state.topics.length >= state.total) {
      return;
    }

    this.stateSubject.next({ ...state, loadingMore: true });

    this.fetchGundem(state.topics.length, state.currentCategory, state.sortBy).subscribe({
      next: (response) => {
        this.stateSubject.next({
          ...this.stateSubject.value,
          topics: [...state.topics, ...(response.topics || [])],
          loadingMore: false
        });
      },
      error: () => {
        this.stateSubject.next({ ...this.stateSubject.value, loadingMore: false });
      }
    });
  }

  private fetchGundem(offset: number, category?: string | null, sortBy?: SortType): Observable<GundemResponse> {
    let params = new HttpParams()
      .set('limit', this.pageSize.toString())
      .set('offset', offset.toString());

    if (category) {
      params = params.set('category', category);
    }

    // Backend-side sorting
    const sortMap: Record<SortType, string> = {
      son: 'latest',
      populer: 'popular'
    };
    params = params.set('sort', sortMap[sortBy || 'son']);

    return this.http.get<GundemResponse>(`${this.baseUrl}/gundem`, { params });
  }

  refresh(): void {
    this.loadInitial(this.stateSubject.value.currentCategory);
  }
}
