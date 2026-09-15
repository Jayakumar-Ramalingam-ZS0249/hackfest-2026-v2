import { CommonModule } from "@angular/common";
import { Component, inject } from "@angular/core";
import { FormBuilder, ReactiveFormsModule, Validators } from "@angular/forms";
import { ActivatedRoute, Router } from "@angular/router";

import { AuthService } from "../../services/auth.service";

@Component({
  selector: "app-login",
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: "./login.component.html",
  styleUrls: ["./login.component.scss"],
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly form = this.fb.group({
    email: ["", [Validators.required, Validators.email]],
    password: ["", [Validators.required]],
  });

  submitting = false;
  showPassword = false;
  errorMessage = "";

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  get emailErrorMessage(): string | null {
    const control = this.form.controls.email;
    if (!control.touched && !control.dirty) {
      return null;
    }
    if (control.hasError("required")) {
      return "Email address is required.";
    }
    if (control.hasError("email")) {
      return "Enter a valid email address.";
    }
    return null;
  }

  get passwordErrorMessage(): string | null {
    const control = this.form.controls.password;
    if (!control.touched && !control.dirty) {
      return null;
    }
    if (control.hasError("required")) {
      return "Password is required.";
    }
    return null;
  }

  submit(): void {
    this.errorMessage = "";

    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const { email, password } = this.form.getRawValue();
    this.submitting = true;

    this.authService.login(email ?? "", password ?? "").subscribe({
      next: (success) => {
        this.submitting = false;
        if (!success) {
          this.errorMessage = "Invalid email or password.";
          return;
        }
        const returnUrl = this.route.snapshot.queryParamMap.get("returnUrl") || "/dashboard";
        this.router.navigateByUrl(returnUrl);
      },
      error: () => {
        this.submitting = false;
        this.errorMessage = "Unable to sign in. Please try again.";
      },
    });
  }
}
