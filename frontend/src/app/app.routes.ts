import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
  {
    path: 'dashboard',
    loadComponent: () => import('./dashboard/dashboard-page').then((m) => m.DashboardPage),
    title: 'Dashboard — Claims Copilot',
  },
  {
    path: 'applications',
    loadComponent: () => import('./applications/applications-page').then((m) => m.ApplicationsPage),
    title: 'Applications — Claims Copilot',
  },
  {
    path: 'applications/:id',
    loadComponent: () => import('./applicant-detail/applicant-detail-page').then((m) => m.ApplicantDetailPage),
    title: 'Applicant detail — Claims Copilot',
  },
  {
    path: 'audit-log',
    loadComponent: () => import('./audit-log/audit-log-page').then((m) => m.AuditLogPage),
    title: 'Audit log — Claims Copilot',
  },
  { path: '**', pathMatch: 'full', redirectTo: 'dashboard' },
];
