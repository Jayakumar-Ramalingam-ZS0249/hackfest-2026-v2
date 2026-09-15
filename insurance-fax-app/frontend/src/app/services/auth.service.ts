import { Injectable } from "@angular/core";
import { BehaviorSubject, Observable, of } from "rxjs";
import { delay } from "rxjs/operators";

import { environment } from "../../environments/environment";

const SESSION_KEY = "mock_auth_session";

export interface MockSession {
  email: string;
  role: string;
  loginAt: string;
}

/**
 * DEV-ONLY MOCK AUTHENTICATION.
 *
 * This app has no backend user/session model at all (no /auth endpoints,
 * no user table). Rather than inventing a fake backend contract, this
 * service is an honest, isolated, frontend-only mock: it accepts exactly
 * one hardcoded dev credential and stores a plain session object in
 * localStorage. It intentionally does NOT talk to the backend.
 *
 * Wiring real authentication would require adding an actual backend
 * endpoint (e.g. POST /api/auth/login) that does not exist yet in this
 * app -- see the `environment.production` gate below.
 */
@Injectable({ providedIn: "root" })
export class AuthService {
  private readonly authenticated$ = new BehaviorSubject<boolean>(false);

  /** Observable auth state for guards/components to subscribe to. */
  readonly isAuthenticated$: Observable<boolean> = this.authenticated$.asObservable();

  private session: MockSession | null = null;

  constructor() {
    // Rehydrate from localStorage so a page refresh doesn't log the user out.
    this.session = this.readStoredSession();
    this.authenticated$.next(this.session !== null);
  }

  login(email: string, password: string): Observable<boolean> {
    // Mock credential check is dev-only. In a production build this branch
    // never runs -- there is no real backend endpoint to call yet, so
    // production login simply fails closed rather than pretending to work.
    if (!environment.production) {
      if (email === "test1@gmail.com" && password === "12345678") {
        const session: MockSession = {
          email,
          role: "Clinical Admin",
          loginAt: new Date().toISOString(),
        };
        this.storeSession(session);
        this.session = session;
        this.authenticated$.next(true);
        return of(true).pipe(delay(300)); // small delay to exercise the loading state
      }
      return of(false).pipe(delay(300));
    }

    // Production: no backend auth endpoint exists yet -- fail closed.
    return of(false);
  }

  logout(): void {
    localStorage.removeItem(SESSION_KEY);
    this.session = null;
    this.authenticated$.next(false);
  }

  isAuthenticated(): boolean {
    return this.authenticated$.value;
  }

  currentUser(): { email: string; role: string } | null {
    if (!this.session) {
      return null;
    }
    return { email: this.session.email, role: this.session.role };
  }

  private storeSession(session: MockSession): void {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  private readStoredSession(): MockSession | null {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) {
      return null;
    }
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.email === "string" && typeof parsed.role === "string") {
        return parsed as MockSession;
      }
      return null;
    } catch {
      return null;
    }
  }
}
