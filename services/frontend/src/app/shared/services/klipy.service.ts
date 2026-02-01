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
  private readonly baseUrl = 'https://api.klipy.com/api/v1';
  private readonly apiKey = environment.klipyApiKey || '';
  private cache = new Map<string, Observable<KlipyGif | null>>();

  constructor(private http: HttpClient) {
    console.log('[KlipyService] API Key loaded:', this.apiKey ? 'YES (' + this.apiKey.substring(0, 8) + '...)' : 'NO (empty)');
  }

  /**
   * Search for a GIF by keyword
   */
  searchGif(query: string): Observable<KlipyGif | null> {
    if (!query || !this.apiKey) {
      console.warn('KlipyService: No query or API key');
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
        // Response structure: { result: true, data: { data: [...] } }
        const items = response?.data?.data;
        if (items && items.length > 0) {
          const item = items[0];
          // Use md (medium) size, fallback to sm (small)
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
        const items = response?.data?.data || [];
        return items.map(item => {
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
        });
      }),
      catchError(() => of([]))
    );
  }
}
