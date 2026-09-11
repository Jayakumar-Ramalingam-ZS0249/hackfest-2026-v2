import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { catchError, of } from 'rxjs';

import { HealthStatus } from '../../models/api-models';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-top-nav',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './top-nav.html',
  styleUrl: './top-nav.scss',
})
export class TopNav {
  private readonly api = inject(ApiService);

  protected readonly health = toSignal(
    this.api.getHealth().pipe(catchError(() => of<HealthStatus | null>(null))),
    { initialValue: null },
  );
}
