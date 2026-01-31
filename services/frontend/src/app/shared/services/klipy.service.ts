import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError, shareReplay } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface KlipyGif {
  id: string;
  title: string;
  url: string;
  mp4: string;
  gif: string;
  webp: string;
  width: number;
  height: number;
}

interface KlipyResponse {
  data: Array<{
    id: string;
    title: string;
    url: string;
    file: {
      mp4?: string;
      gif?: string;
      webp?: string;
    };
    width?: number;
    height?: number;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class KlipyService {
  private readonly baseUrl = 'https://api.klipy.com/api/v1';
  private readonly apiKey = environment.klipyApiKey || '';
  private cache = new Map<string, Observable<KlipyGif | null>>();

  constructor(private http: HttpClient) {}

  /**
   * Search for a GIF by keyword
   */
  searchGif(query: string): Observable<KlipyGif | null> {
    if (!query || !this.apiKey) {
      return of(null);
    }

    const cacheKey = query.toLowerCase().trim();

    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!;
    }

    const url = `${this.baseUrl}/${this.apiKey}/gifs/search`;
    const params = {
      q: query,
      per_page: '1',
      locale: 'tr',
      content_filter: 'high'
    };

    const request$ = this.http.get<KlipyResponse>(url, { params }).pipe(
      map(response => {
        if (response.data && response.data.length > 0) {
          const item = response.data[0];
          return {
            id: item.id,
            title: item.title,
            url: item.url,
            mp4: item.file?.mp4 || '',
            gif: item.file?.gif || '',
            webp: item.file?.webp || '',
            width: item.width || 200,
            height: item.height || 200
          };
        }
        return null;
      }),
      catchError(() => of(null)),
      shareReplay(1)
    );

    this.cache.set(cacheKey, request$);
    return request$;
  }

  /**
   * Get trending GIFs
   */
  getTrending(limit: number = 10): Observable<KlipyGif[]> {
    if (!this.apiKey) {
      return of([]);
    }

    const url = `${this.baseUrl}/${this.apiKey}/gifs/trending`;
    const params = {
      per_page: limit.toString(),
      locale: 'tr'
    };

    return this.http.get<KlipyResponse>(url, { params }).pipe(
      map(response => {
        return (response.data || []).map(item => ({
          id: item.id,
          title: item.title,
          url: item.url,
          mp4: item.file?.mp4 || '',
          gif: item.file?.gif || '',
          webp: item.file?.webp || '',
          width: item.width || 200,
          height: item.height || 200
        }));
      }),
      catchError(() => of([]))
    );
  }
}
