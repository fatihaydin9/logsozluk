import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { switchMap, shareReplay } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { Topic, GundemResponse } from '../../shared/models';

@Injectable({
  providedIn: 'root'
})
export class GundemService {
  private baseUrl = environment.apiUrl;

  // State management with Signals pattern using RxJS
  private refreshSubject = new BehaviorSubject<void>(undefined);

  // Declarative data streams
  readonly gundem$ = this.refreshSubject.pipe(
    switchMap(() => this.fetchGundem()),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  constructor(private http: HttpClient) {}

  private fetchGundem(limit = 50, offset = 0): Observable<GundemResponse> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());
    return this.http.get<GundemResponse>(`${this.baseUrl}/gundem`, { params });
  }

  refresh(): void {
    this.refreshSubject.next();
  }
}
