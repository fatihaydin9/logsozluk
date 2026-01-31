import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, combineLatest } from 'rxjs';
import { switchMap, map, shareReplay, distinctUntilChanged } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Topic, Entry, TopicResponse } from '../../shared/models';

interface TopicState {
  slug: string;
  limit: number;
  offset: number;
}

@Injectable({
  providedIn: 'root'
})
export class TopicService {
  private baseUrl = environment.apiUrl;

  // State management
  private stateSubject = new BehaviorSubject<TopicState>({ slug: '', limit: 50, offset: 0 });

  // Selectors
  readonly slug$ = this.stateSubject.pipe(
    map(state => state.slug),
    distinctUntilChanged()
  );

  // Main data stream - declarative pattern
  readonly topicData$ = this.stateSubject.pipe(
    distinctUntilChanged((prev, curr) =>
      prev.slug === curr.slug &&
      prev.limit === curr.limit &&
      prev.offset === curr.offset
    ),
    switchMap(state => this.fetchTopicData(state)),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly topic$ = this.topicData$.pipe(
    map(response => response.topic)
  );

  readonly entries$ = this.topicData$.pipe(
    map(response => response.entries)
  );

  readonly hasMore$ = combineLatest([
    this.topicData$,
    this.stateSubject
  ]).pipe(
    map(([response, state]) => {
      const totalLoaded = state.offset + response.entries.length;
      return totalLoaded < response.pagination.total;
    })
  );

  constructor(private http: HttpClient) {}

  private fetchTopicData(state: TopicState): Observable<TopicResponse> {
    if (!state.slug) {
      throw new Error('Slug is required');
    }

    const params = new HttpParams()
      .set('limit', state.limit.toString())
      .set('offset', state.offset.toString());

    return this.http.get<TopicResponse>(
      `${this.baseUrl}/topics/${state.slug}/entries`,
      { params }
    );
  }

  loadTopic(slug: string): void {
    this.stateSubject.next({ slug, limit: 50, offset: 0 });
  }

  loadMore(): void {
    const currentState = this.stateSubject.value;
    this.stateSubject.next({
      ...currentState,
      offset: currentState.offset + currentState.limit
    });
  }

  reset(): void {
    this.stateSubject.next({ slug: '', limit: 50, offset: 0 });
  }
}
