import { inject } from "@angular/core";
import { CanActivateFn, Router } from "@angular/router";

import { AuthService } from "../services/auth.service";

/**
 * Protects authenticated-only routes. If the user has no mock session,
 * redirect to /login and preserve the attempted URL as a returnUrl query
 * param so login can send them back afterwards.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(["/login"], { queryParams: { returnUrl: state.url } });
};

/**
 * Prevents an already-authenticated user from visiting /login again --
 * sends them straight to /dashboard instead.
 */
export const guestGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (!authService.isAuthenticated()) {
    return true;
  }

  return router.createUrlTree(["/dashboard"]);
};
