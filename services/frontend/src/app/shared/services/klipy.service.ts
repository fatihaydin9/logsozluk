import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError, shareReplay } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface KlipyGif {
  id: string;
  title: string;
  mp4: string;
  gif: string;
  webp: string;
  width: number;
  height: number;
}

interface KlipyFileFormat {
  url: string;
  width: number;
  height: number;
  size: number;
}

interface KlipyItem {
  id: number;
  slug: string;
  title: string;
  file: {
    hd?: { mp4?: KlipyFileFormat; gif?: KlipyFileFormat; webp?: KlipyFileFormat };
    md?: { mp4?: KlipyFileFormat; gif?: KlipyFileFormat; webp?: KlipyFileFormat };
    sm?: { mp4?: KlipyFileFormat; gif?: KlipyFileFormat; webp?: KlipyFileFormat };
  };
}

interface KlipyResponse {
  result: boolean;
  data: {
    data: KlipyItem[];
    current_page: number;
    per_page: number;
    has_next: boolean;
  };
}

@Injectable({
  providedIn: 'root'
})
export class KlipyService {
  private readonly proxyUrl = `${environment.apiUrl}/gifs/search`;
  private cache = new Map<string, Observable<KlipyGif | null>>();

  constructor(private http: HttpClient) {}

  /**
   * Search for a GIF by keyword (via backend proxy — API key stays server-side)
   */
  searchGif(query: string): Observable<KlipyGif | null> {
    if (!query) {
      return of(null);
    }

    const cacheKey = query.toLowerCase().trim();

    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey)!;
    }

    const request$ = this.http.get<KlipyResponse>(this.proxyUrl, { params: { q: query } }).pipe(
      map(response => {
        const items = response?.data?.data;
        if (items && items.length > 0) {
          const item = items[0];
          const file = item.file?.md || item.file?.sm || item.file?.hd;
          return {
            id: String(item.id),
            title: item.title || '',
            mp4: file?.mp4?.url || '',
            gif: file?.gif?.url || '',
            webp: file?.webp?.url || '',
            width: file?.mp4?.width || file?.gif?.width || 200,
            height: file?.mp4?.height || file?.gif?.height || 200
          };
        }
        return null;
      }),
      catchError(err => {
        console.error('KlipyService error:', err);
        return of(null);
      }),
      shareReplay(1)
    );

    this.cache.set(cacheKey, request$);
    return request$;
  }
}
