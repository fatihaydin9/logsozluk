import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { switchMap, shareReplay, map } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Debbe, DebbeResponse } from '../../shared/models';

@Injectable({
  providedIn: 'root'
})
export class DebbeService {
  private baseUrl = environment.apiUrl;

  private refreshSubject = new BehaviorSubject<void>(undefined);

  private readonly debbeData$ = this.refreshSubject.pipe(
    switchMap(() => this.fetchDebbes()),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  readonly debbes$ = this.debbeData$.pipe(
    map(response => response.debbes)
  );

  readonly date$ = this.debbeData$.pipe(
    map(response => response.date)
  );

  constructor(private http: HttpClient) {}

  private fetchDebbes(): Observable<DebbeResponse> {
    return this.http.get<DebbeResponse>(`${this.baseUrl}/debbe`);
  }

  refresh(): void {
    this.refreshSubject.next();
  }
}
