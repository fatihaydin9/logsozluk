import { Injectable } from '@angular/core';
import { BehaviorSubject, interval } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class SystemTimeService {
  private readonly startTime: Date;
  private uptimeSubject = new BehaviorSubject<string>('00:00:00');

  uptime$ = this.uptimeSubject.asObservable();

  constructor() {
    // Uygulama başlangıç zamanını kaydet
    this.startTime = new Date();

    // Her saniye uptime'ı güncelle
    interval(1000).pipe(
      startWith(0),
      map(() => this.calculateUptime())
    ).subscribe(uptime => this.uptimeSubject.next(uptime));
  }

  private calculateUptime(): string {
    const now = new Date();
    const diffMs = now.getTime() - this.startTime.getTime();

    const totalSeconds = Math.floor(diffMs / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return `${this.pad(hours)}:${this.pad(minutes)}:${this.pad(seconds)}`;
  }

  private pad(num: number): string {
    return num.toString().padStart(2, '0');
  }

  getStartTime(): Date {
    return this.startTime;
  }

  getUptimeSeconds(): number {
    return Math.floor((new Date().getTime() - this.startTime.getTime()) / 1000);
  }
}
