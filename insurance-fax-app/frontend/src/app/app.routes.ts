import { Routes } from "@angular/router";

import { authGuard, guestGuard } from "./guards/auth.guard";

export const routes: Routes = [
  {
    path: "",
    pathMatch: "full",
    loadComponent: () => import("./pages/landing/landing.component").then((m) => m.LandingComponent),
  },
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
    path: "growth-studio",
    loadComponent: () => import("./pages/growth-studio/growth-studio.component").then((m) => m.GrowthStudioComponent),
    canActivate: [authGuard],
  },
  {
    path: "governance",
    loadComponent: () => import("./pages/governance/governance.component").then((m) => m.GovernanceComponent),
    canActivate: [authGuard],
  },
  {
    path: "managed-operations",
    loadComponent: () =>
      import("./pages/managed-operations/managed-operations.component").then((m) => m.ManagedOperationsComponent),
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
