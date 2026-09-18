import { Component, HostListener, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import { filter } from "rxjs/operators";

import { DashboardStatistics, FaxService } from "./services/fax.service";
import { AuthService } from "./services/auth.service";

const THEME_KEY = "theme_preference";

@Component({
  selector: "app-root",
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.scss"],
})
export class AppComponent implements OnInit {
  backendConnected: boolean | null = null;
  aiProviderLabel = "checking…";
  stats: DashboardStatistics | null = null;

  userMenuOpen = false;
  isDarkMode = false;

  // Sidebar becomes an off-canvas drawer below 768px (see app.component.scss)
  // -- this just tracks whether it's currently slid open.
  mobileNavOpen = false;

  constructor(private faxService: FaxService, private router: Router, private authService: AuthService) {}

  ngOnInit(): void {
    this.checkHealth();
    this.refreshStats();
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
      this.refreshStats();
      this.mobileNavOpen = false;
    });
    this.initTheme();
  }

  get currentUser() {
    return this.authService.currentUser();
  }

  get userInitials(): string {
    const email = this.currentUser?.email;
    if (!email) return "?";
    const local = email.split("@")[0];
    return local.slice(0, 2).toUpperCase();
  }

  // The shell (header/sidebar) wraps every route, including /login and the
  // "/" landing splash, since this app has no nested layout routes. Hide
  // the authenticated chrome on those two so each renders as its own
  // full-bleed screen instead of sitting inside the app frame.
  get isLoginPage(): boolean {
    return this.router.url.split("?")[0].startsWith("/login");
  }

  get isLandingPage(): boolean {
    return this.router.url.split("?")[0] === "/";
  }

  get hideShell(): boolean {
    return this.isLoginPage || this.isLandingPage;
  }

  toggleMobileNav(event: MouseEvent): void {
    event.stopPropagation();
    this.mobileNavOpen = !this.mobileNavOpen;
  }

  closeMobileNav(): void {
    this.mobileNavOpen = false;
  }

  toggleUserMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.userMenuOpen = !this.userMenuOpen;
  }

  @HostListener("document:click")
  closeMenus(): void {
    this.userMenuOpen = false;
  }

  logout(): void {
    this.authService.logout();
    this.userMenuOpen = false;
    this.router.navigateByUrl("/login");
  }

  toggleTheme(): void {
    this.isDarkMode = !this.isDarkMode;
    this.applyTheme(this.isDarkMode);
    localStorage.setItem(THEME_KEY, this.isDarkMode ? "dark" : "light");
  }

  private initTheme(): void {
    const stored = localStorage.getItem(THEME_KEY);
    this.isDarkMode = stored === "dark";
    this.applyTheme(this.isDarkMode);
  }

  private applyTheme(dark: boolean): void {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }

  private checkHealth() {
    this.faxService.getHealth().subscribe({
      next: (res) => {
        this.backendConnected = true;
        this.aiProviderLabel = res.aiProvider;
      },
      error: () => {
        this.backendConnected = false;
        this.aiProviderLabel = "unavailable";
      },
    });
  }

  private refreshStats() {
    this.faxService.getDashboardStatistics().subscribe({
      next: (stats) => (this.stats = stats),
      error: () => {},
    });
  }
}
