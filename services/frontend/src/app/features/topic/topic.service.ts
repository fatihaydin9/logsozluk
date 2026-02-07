import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { switchMap, map, tap, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Topic, Entry, TopicResponse } from '../../shared/models';

interface TopicState {
  topic: Topic | null;
  entries: Entry[];
  total: number;
  loading: boolean;
  loadingMore: boolean;
  currentSlug: string;
}

const initialState: TopicState = {
  topic: null,
  entries: [],
  total: 0,
  loading: false,
  loadingMore: false,
  currentSlug: ''
};

@Injectable({
  providedIn: 'root'
})
export class TopicService {
  private baseUrl = environment.apiUrl;
  private pageSize = 50;

  private stateSubject = new BehaviorSubject<TopicState>(initialState);

  readonly topic$ = this.stateSubject.pipe(map(s => s.topic));
  readonly entries$ = this.stateSubject.pipe(map(s => s.entries));
  readonly loading$ = this.stateSubject.pipe(map(s => s.loading));
  readonly loadingMore$ = this.stateSubject.pipe(map(s => s.loadingMore));
  readonly hasMore$ = this.stateSubject.pipe(
    map(s => s.entries.length < s.total)
  );

  constructor(private http: HttpClient) {}

  loadTopic(slug: string): void {
    // Her zaman güncel veriyi çek (comment sayıları değişmiş olabilir)
    this.stateSubject.next({
      ...initialState,
      loading: true,
      currentSlug: slug
    });

    this.fetchEntries(slug, 0).subscribe({
      next: (response) => {
        this.stateSubject.next({
          topic: response.topic,
          entries: response.entries,
          total: response.pagination?.total || response.entries.length,
          loading: false,
          loadingMore: false,
          currentSlug: slug
        });
      },
      error: () => {
        this.stateSubject.next({
          ...this.stateSubject.value,
          loading: false
        });
      }
    });
  }

  loadMore(): void {
    const state = this.stateSubject.value;

    // Zaten yükleniyor veya daha fazla yok
    if (state.loadingMore || state.loading || state.entries.length >= state.total) {
      return;
    }

    this.stateSubject.next({ ...state, loadingMore: true });

    this.fetchEntries(state.currentSlug, state.entries.length).subscribe({
      next: (response) => {
        this.stateSubject.next({
          ...this.stateSubject.value,
          entries: [...state.entries, ...response.entries], // Biriktir!
          loadingMore: false
        });
      },
      error: () => {
        this.stateSubject.next({
          ...this.stateSubject.value,
          loadingMore: false
        });
      }
    });
  }

  private fetchEntries(slug: string, offset: number): Observable<TopicResponse> {
    const params = new HttpParams()
      .set('limit', this.pageSize.toString())
      .set('offset', offset.toString());

    return this.http.get<TopicResponse>(
      `${this.baseUrl}/topics/${slug}/entries`,
      { params }
    );
  }

  reset(): void {
    this.stateSubject.next(initialState);
  }
}
