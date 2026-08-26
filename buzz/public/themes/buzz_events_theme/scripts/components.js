document.addEventListener("alpine:init", () => {
	Alpine.data("stickyCta", () => ({
		visible: false,
		init() {
			const hero = document.getElementById("hero");
			if (!hero) {
				const onScroll = () => {
					this.visible = window.scrollY > 240;
				};
				window.addEventListener("scroll", onScroll, { passive: true });
				return;
			}
			const observer = new IntersectionObserver(
				([entry]) => {
					this.visible = !entry.isIntersecting;
				},
				{ rootMargin: "-40% 0px 0px 0px" }
			);
			observer.observe(hero);
		},
	}));

	Alpine.data("eventFilter", () => ({
		filter: "upcoming",
		set(value) {
			this.filter = value;
		},
		matches(status) {
			return this.filter === "all" || this.filter === status;
		},
	}));

	Alpine.data("loginDialog", () => ({
		open: false,
		view: "login",
		loading: false,
		error: "",
		success: "",
		form: { email: "", password: "", full_name: "" },
		context: null,
		async loadContext() {
			if (this.context) return;
			try {
				const response = await fetch(
					`/api/method/buzz.api.auth.get_login_context?redirect_to=${encodeURIComponent(
						window.location.href
					)}`,
					{ headers: { "X-Frappe-CSRF-Token": this.csrf() } }
				);
				const data = await response.json().catch(() => ({}));
				this.context = data?.message || {};
			} catch (error) {
				this.context = {};
			}
		},
		show() {
			this.open = true;
			this.view = "login";
			this.reset();
			this.loadContext();
		},
		hide() {
			this.open = false;
		},
		switchView(view) {
			this.view = view;
			this.error = "";
			this.success = "";
		},
		reset() {
			this.error = "";
			this.success = "";
			this.form = { email: "", password: "", full_name: "" };
		},
		titleFor() {
			return {
				login: "Login to continue",
				signup: "Create account",
				forgot: "Reset password",
			}[this.view];
		},
		labelFor() {
			return { login: "Sign in", signup: "New account", forgot: "Password reset" }[
				this.view
			];
		},
		csrf() {
			return document.querySelector('meta[name="csrf-token"]')?.content || "";
		},
		parseError(data, fallback) {
			if (data?._server_messages) {
				try {
					const messages = JSON.parse(data._server_messages);
					if (messages.length) return JSON.parse(messages[0]).message || fallback;
				} catch (error) {}
			}
			return data?.message || fallback;
		},
		async submitLogin() {
			this.loading = true;
			this.error = "";
			try {
				const response = await fetch("/api/method/login", {
					method: "POST",
					headers: {
						"Content-Type": "application/x-www-form-urlencoded",
						"X-Frappe-CSRF-Token": this.csrf(),
					},
					body: new URLSearchParams({ usr: this.form.email, pwd: this.form.password }),
				});
				if (response.ok) {
					window.location.reload();
					return;
				}
				const data = await response.json().catch(() => ({}));
				this.error = this.parseError(data, "Invalid email or password");
			} catch (error) {
				this.error = error.message || "Network error";
			} finally {
				this.loading = false;
			}
		},
		async submitSignup() {
			this.loading = true;
			this.error = "";
			this.success = "";
			try {
				const response = await fetch("/api/method/frappe.core.doctype.user.user.sign_up", {
					method: "POST",
					headers: {
						"Content-Type": "application/x-www-form-urlencoded",
						"X-Frappe-CSRF-Token": this.csrf(),
					},
					body: new URLSearchParams({
						email: this.form.email,
						full_name: this.form.full_name,
						redirect_to: window.location.pathname,
					}),
				});
				const data = await response.json().catch(() => ({}));
				if (response.ok) {
					this.success = "Check your email to verify your account.";
				} else {
					this.error = this.parseError(data, "Could not sign up. Try again.");
				}
			} catch (error) {
				this.error = error.message || "Network error";
			} finally {
				this.loading = false;
			}
		},
		async submitForgot() {
			this.loading = true;
			this.error = "";
			this.success = "";
			try {
				const response = await fetch(
					"/api/method/frappe.core.doctype.user.user.reset_password",
					{
						method: "POST",
						headers: {
							"Content-Type": "application/x-www-form-urlencoded",
							"X-Frappe-CSRF-Token": this.csrf(),
						},
						body: new URLSearchParams({ user: this.form.email }),
					}
				);
				const data = await response.json().catch(() => ({}));
				if (response.ok) {
					this.success = "Password reset link sent to your email.";
				} else {
					this.error = this.parseError(data, "Could not send reset link.");
				}
			} catch (error) {
				this.error = error.message || "Network error";
			} finally {
				this.loading = false;
			}
		},
		async logout() {
			try {
				await fetch("/api/method/logout", {
					method: "POST",
					headers: { "X-Frappe-CSRF-Token": this.csrf() },
				});
			} finally {
				window.location.reload();
			}
		},
	}));
});
