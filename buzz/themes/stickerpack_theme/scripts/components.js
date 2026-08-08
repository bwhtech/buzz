document.addEventListener("alpine:init", function () {
	Alpine.data("stickyCta", function () {
		return {
			visible: false,
			init: function () {
				var self = this;
				var hero = document.getElementById("hero");
				function update() {
					if (!hero) {
						self.visible = window.scrollY > 240;
						return;
					}
					var rect = hero.getBoundingClientRect();
					self.visible = rect.bottom < 80;
				}
				window.addEventListener("scroll", update, { passive: true });
				update();
			},
		};
	});

	Alpine.data("eventFilter", function () {
		return {
			filter: "upcoming",
			set: function (value) {
				this.filter = value;
			},
			matches: function (status) {
				return this.filter === "all" || this.filter === status;
			},
		};
	});

	Alpine.data("loginDialog", function () {
		return {
			open: false,
			view: "login",
			loading: false,
			error: "",
			success: "",
			form: { email: "", password: "", full_name: "" },
			context: null,
			csrf: function () {
				var element = document.querySelector('meta[name="csrf-token"]');
				return element ? element.getAttribute("content") : "";
			},
			async loadContext() {
				if (this.context) return;
				try {
					const response = await fetch(
						"/api/method/buzz.api.auth.get_login_context?redirect_to=" +
							encodeURIComponent(window.location.href),
						{ headers: { "X-Frappe-CSRF-Token": this.csrf() } }
					);
					const data = await response.json().catch(() => ({}));
					this.context = (data && data.message) || {};
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
				return { login: "scribble in", signup: "fresh page", forgot: "lost the page?" }[
					this.view
				];
			},
			labelFor() {
				return { login: "sign in", signup: "new sketch", forgot: "reset" }[this.view];
			},
			parseError(data, fallback) {
				if (data && data._server_messages) {
					try {
						const messages = JSON.parse(data._server_messages);
						if (messages.length) return JSON.parse(messages[0]).message || fallback;
					} catch (error) {}
				}
				return (data && data.message) || fallback;
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
						body: new URLSearchParams({
							usr: this.form.email,
							pwd: this.form.password,
						}),
					});
					if (response.ok) {
						window.location.reload();
						return;
					}
					const data = await response.json().catch(() => ({}));
					this.error = this.parseError(data, "wrong email or password");
				} catch (error) {
					this.error = error.message || "network hiccup";
				} finally {
					this.loading = false;
				}
			},
			async submitSignup() {
				this.loading = true;
				this.error = "";
				this.success = "";
				try {
					const response = await fetch(
						"/api/method/frappe.core.doctype.user.user.sign_up",
						{
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
						}
					);
					const data = await response.json().catch(() => ({}));
					if (response.ok) this.success = "check your email to verify.";
					else this.error = this.parseError(data, "couldn't sign up. try again.");
				} catch (error) {
					this.error = error.message || "network hiccup";
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
					if (response.ok) this.success = "reset link sent.";
					else this.error = this.parseError(data, "couldn't send link.");
				} catch (error) {
					this.error = error.message || "network hiccup";
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
		};
	});
});
