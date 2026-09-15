import { Routes } from "@angular/router";

import { authGuard, guestGuard } from "./guards/auth.guard";

export const routes: Routes = [
  { path: "", pathMatch: "full", redirectTo: "dashboard" },
  {
    path: "login",
    loadComponent: () => import("./pages/login/login.component").then((m) => m.LoginComponent),
    canActivate: [guestGuard],
  },
  {
    path: "dashboard",
    loadComponent: () => import("./pages/dashboard/dashboard.component").then((m) => m.DashboardComponent),
    canActivate: [authGuard],
  },
  {
    path: "queue/:filter",
    loadComponent: () => import("./pages/claim-queue/claim-queue.component").then((m) => m.ClaimQueueComponent),
    canActivate: [authGuard],
  },
  {
    path: "queue/:filter/:id",
    loadComponent: () => import("./pages/claim-queue/claim-queue.component").then((m) => m.ClaimQueueComponent),
    canActivate: [authGuard],
  },
  { path: "**", redirectTo: "dashboard" },
];
