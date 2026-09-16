import { Component, HostListener, OnInit } from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from "@angular/router";
import { Subject } from "rxjs";
import { debounceTime, filter } from "rxjs/operators";

import { AttentionSummary, DashboardStatistics, FaxService, FaxSummary } from "./services/fax.service";
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

  // Real global search -- filters the already-fetched claim list by id,
  // filename, or extracted patient name. No backend round-trip per
  // keystroke, and never a fabricated result.
  searchQuery = "";
  searchOpen = false;
  private allClaims: FaxSummary[] = [];
  private searchInput$ = new Subject<string>();

  // Real notification bell -- backed by /api/dashboard/attention-summary,
  // the same "needs attention" logic the dashboard uses. Never a fake badge count.
  attention: AttentionSummary | null = null;
  notificationsOpen = false;

  constructor(private faxService: FaxService, private router: Router, private authService: AuthService) {}

  ngOnInit(): void {
    this.checkHealth();
    this.refreshStats();
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
      this.refreshStats();
      this.mobileNavOpen = false;
    });
    this.initTheme();
    this.searchInput$.pipe(debounceTime(200)).subscribe((q) => (this.searchQuery = q));
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

  get searchResults(): FaxSummary[] {
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return [];
    return this.allClaims
      .filter(
        (c) =>
          !c.deleted &&
          (c.id.toLowerCase().includes(q) ||
            c.filename.toLowerCase().includes(q) ||
            (c.patientName || "").toLowerCase().includes(q)),
      )
      .slice(0, 8);
  }

  // The shell (header/sidebar) wraps every route, including /login, since
  // this app has no nested layout routes. Hide the authenticated chrome on
  // the login screen so it renders as a proper full-bleed split view.
  get isLoginPage(): boolean {
    return this.router.url.split("?")[0].startsWith("/login");
  }

  onSearchInput(value: string): void {
    this.searchInput$.next(value);
    this.searchOpen = value.trim().length > 0;
  }

  selectSearchResult(claimId: string): void {
    this.searchOpen = false;
    this.searchQuery = "";
    this.router.navigate(["/queue/all", claimId]);
  }

  toggleNotifications(event: MouseEvent): void {
    event.stopPropagation();
    this.userMenuOpen = false;
    this.notificationsOpen = !this.notificationsOpen;
  }

  goToAttentionItem(claimId: string): void {
    this.notificationsOpen = false;
    this.router.navigate(["/queue/all", claimId]);
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
    this.notificationsOpen = false;
    this.userMenuOpen = !this.userMenuOpen;
  }

  @HostListener("document:click")
  closeMenus(): void {
    this.userMenuOpen = false;
    this.notificationsOpen = false;
    this.searchOpen = false;
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
    this.faxService.listFaxes("all").subscribe({
      next: (claims) => (this.allClaims = claims),
      error: () => {},
    });
    this.faxService.getAttentionSummary().subscribe({
      next: (attention) => (this.attention = attention),
      error: () => {},
    });
  }
}
