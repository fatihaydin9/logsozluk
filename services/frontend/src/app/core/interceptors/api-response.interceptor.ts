import { HttpInterceptorFn } from '@angular/common/http';
import { map } from 'rxjs/operators';

export const apiResponseInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    map((event: any) => {
      // Unwrap API response: { data: ..., success: true } -> data
      if (event.body && typeof event.body === 'object' && 'data' in event.body && 'success' in event.body) {
        return event.clone({ body: event.body.data });
      }
      return event;
    })
  );
};
