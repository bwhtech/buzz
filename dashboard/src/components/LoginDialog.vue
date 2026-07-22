<template>
	<Dialog v-model="is_open" size="md" @after-leave="resetState">
		<template #title>
			<h3 class="text-2xl-semibold text-ink-gray-9">
				{{ view_title }}
			</h3>
		</template>
		<div
			v-if="login_context?.login_banner"
			class="rounded-md bg-surface-gray-2 p-3 prose prose-sm max-w-none mb-6"
			v-html="login_context.login_banner"
		/>

		<div
			v-if="error_message"
			class="mb-4 rounded-md bg-surface-red-2 p-3 text-sm text-ink-red-6"
		>
			{{ error_message }}
		</div>

		<div
			v-if="success_message"
			class="mb-4 rounded-md bg-surface-green-2 p-3 text-sm text-ink-green-6"
		>
			{{ success_message }}
		</div>

		<form v-if="current_view === 'login'" class="space-y-4" @submit.prevent="handleLogin">
			<template v-if="!login_context?.disable_user_pass_login">
				<FormControl
					type="email"
					:label="__('Email')"
					:placeholder="__('Enter your email')"
					v-model="form.email"
					required
					@keydown.enter="focusPassword"
				/>
				<FormControl
					ref="password_input"
					type="password"
					:label="__('Password')"
					:placeholder="__('Enter your password')"
					v-model="form.password"
					required
				/>
				<div class="flex justify-end">
					<button
						type="button"
						class="text-sm text-ink-gray-5 hover:text-ink-gray-7"
						@click="switchView('forgot-password')"
					>
						{{ __("Forgot Password?") }}
					</button>
				</div>
				<Button
					variant="solid"
					class="w-full"
					type="submit"
					:loading="session.login.loading"
				>
					{{ __("Login") }}
				</Button>
			</template>

			<template v-if="has_social_logins || login_context?.login_with_email_link">
				<div class="relative flex items-center justify-center">
					<div class="absolute inset-0 flex items-center">
						<div class="w-full border-t border-outline-gray-2" />
					</div>
					<span class="relative bg-surface-elevation-2 px-2 text-sm text-ink-gray-4">
						{{ __("or") }}
					</span>
				</div>

				<SocialLoginButtons :provider_logins="login_context?.provider_logins" />

				<template v-if="login_context?.login_with_email_link">
					<Button
						variant="subtle"
						class="w-full"
						type="button"
						@click="switchView('email-link')"
					>
						{{ __("Login with Email Link") }}
					</Button>
				</template>
			</template>

			<div v-if="!login_context?.disable_signup" class="text-center text-sm text-ink-gray-5">
				{{ __("Don't have an account?") }}
				<button
					type="button"
					class="font-semibold text-ink-gray-9 hover:text-ink-gray-8"
					@click="switchView('signup')"
				>
					{{ __("Sign up") }}
				</button>
			</div>
		</form>

		<form
			v-else-if="current_view === 'signup'"
			class="space-y-4"
			@submit.prevent="handleSignup"
		>
			<FormControl
				type="text"
				:label="__('Full Name')"
				:placeholder="__('Enter your full name')"
				v-model="form.full_name"
				required
			/>
			<FormControl
				type="email"
				:label="__('Email')"
				:placeholder="__('Enter your email')"
				v-model="form.email"
				required
			/>
			<Button
				variant="solid"
				class="w-full"
				type="submit"
				:loading="signup_resource.loading"
			>
				{{ __("Sign Up") }}
			</Button>

			<template v-if="has_social_logins">
				<div class="relative flex items-center justify-center">
					<div class="absolute inset-0 flex items-center">
						<div class="w-full border-t border-outline-gray-2" />
					</div>
					<span class="relative bg-surface-elevation-2 px-2 text-sm text-ink-gray-4">
						{{ __("or") }}
					</span>
				</div>

				<SocialLoginButtons :provider_logins="login_context?.provider_logins" />
			</template>

			<div class="text-center text-sm text-ink-gray-5">
				{{ __("Already have an account?") }}
				<button
					type="button"
					class="font-medium text-ink-gray-7 hover:text-ink-gray-9"
					@click="switchView('login')"
				>
					{{ __("Login") }}
				</button>
			</div>
		</form>

		<form
			v-else-if="current_view === 'forgot-password'"
			class="space-y-4"
			@submit.prevent="handleForgotPassword"
		>
			<p class="text-sm text-ink-gray-5">
				{{
					__(
						"Enter your email address and we'll send you a link to reset your password."
					)
				}}
			</p>
			<FormControl
				type="email"
				:label="__('Email')"
				:placeholder="__('Enter your email')"
				v-model="form.email"
				required
			/>
			<Button
				variant="solid"
				class="w-full"
				type="submit"
				:loading="forgot_password_resource.loading"
			>
				{{ __("Reset Password") }}
			</Button>
			<div class="text-center">
				<button
					type="button"
					class="text-sm text-ink-gray-5 hover:text-ink-gray-7"
					@click="switchView('login')"
				>
					{{ __("Back to Login") }}
				</button>
			</div>
		</form>

		<form
			v-else-if="current_view === 'email-link'"
			class="space-y-4"
			@submit.prevent="handleEmailLink"
		>
			<p class="text-sm text-ink-gray-5">
				{{ __("We'll send you a one-time login link to your email address.") }}
			</p>
			<FormControl
				type="email"
				:label="__('Email')"
				:placeholder="__('Enter your email')"
				v-model="form.email"
				required
			/>
			<Button
				variant="solid"
				class="w-full"
				type="submit"
				:loading="email_link_resource.loading"
			>
				{{ __("Send Login Link") }}
			</Button>
			<div class="text-center">
				<button
					type="button"
					class="text-sm text-ink-gray-5 hover:text-ink-gray-7"
					@click="switchView('login')"
				>
					{{ __("Back to Login") }}
				</button>
			</div>
		</form>
	</Dialog>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { useLoginDialog } from "@/composables/useLoginDialog";
import { session } from "@/data/session";
import { userResource } from "@/data/user";
import { Button, Dialog, FormControl, createResource } from "frappe-ui";
import {
	type ComponentPublicInstance,
	type PropType,
	computed,
	defineComponent,
	h,
	ref,
	watch,
} from "vue";

type LoginView = "login" | "signup" | "forgot-password" | "email-link";

interface ProviderLogin {
	auth_url: string;
	icon?: string;
	provider_name: string;
}

const { is_open, close } = useLoginDialog();

const current_view = ref<LoginView>("login");
const error_message = ref("");
const success_message = ref("");
const password_input = ref<ComponentPublicInstance | null>(null);

const form = ref({
	email: "",
	password: "",
	full_name: "",
});

const view_title = computed(() => {
	const titles = {
		login: __("Login to Continue"),
		signup: __("Create Account"),
		"forgot-password": __("Forgot Password"),
		"email-link": __("Login with Email Link"),
	};
	return titles[current_view.value] || __("Login");
});

const login_context_resource = createResource({
	url: "buzz.api.auth.get_login_context",
	params: { redirect_to: window.location.href },
	auto: true,
});

const login_context = computed(() => login_context_resource.data);

const has_social_logins = computed(() => login_context.value?.provider_logins?.length > 0);

const SocialLoginButtons = defineComponent({
	props: { provider_logins: Array as PropType<ProviderLogin[]> },
	setup(props) {
		return () =>
			(props.provider_logins || []).map((provider) =>
				h(
					Button,
					{
						variant: "subtle",
						class: "w-full",
						type: "button",
						onClick: () => {
							window.location.href = provider.auth_url;
						},
					},
					{
						...(provider.icon
							? {
									prefix: () =>
										h("img", {
											src: provider.icon,
											class: "h-4 w-4",
											alt: provider.provider_name,
										}),
							  }
							: {}),
						default: () => __("Continue with {0}", [provider.provider_name]),
					}
				)
			);
	},
});

function focusPassword() {
	password_input.value?.$el?.querySelector("input")?.focus();
}

function switchView(view: LoginView) {
	current_view.value = view;
	error_message.value = "";
	success_message.value = "";
}

function resetState() {
	current_view.value = "login";
	error_message.value = "";
	success_message.value = "";
	form.value = { email: "", password: "", full_name: "" };
}

function handleLogin() {
	error_message.value = "";
	session.login.submit(
		{ email: form.value.email, password: form.value.password },
		{
			onSuccess() {
				userResource.reload();
				session.user =
					session.login.data?.user || document.cookie.match(/user_id=([^;]+)/)?.[1];
				close();
			},
			onError(error: FrappeError) {
				error_message.value = error.messages?.[0] || __("Invalid email or password.");
			},
		}
	);
}

const signup_resource = createResource({
	url: "frappe.core.doctype.user.user.sign_up",
});

function handleSignup() {
	error_message.value = "";
	signup_resource.submit(
		{
			email: form.value.email,
			full_name: form.value.full_name,
			redirect_to: window.location.pathname,
		},
		{
			onSuccess(data: any[]) {
				if (data && data[0] === 1) {
					success_message.value = __("Please check your email to verify your account.");
				} else if (data && data[1]) {
					success_message.value = data[1];
				} else {
					success_message.value = __("Please check your email to verify your account.");
				}
			},
			onError(error: FrappeError) {
				error_message.value =
					error.messages?.[0] || __("Something went wrong. Please try again.");
			},
		}
	);
}

const forgot_password_resource = createResource({
	url: "frappe.core.doctype.user.user.reset_password",
});

function handleForgotPassword() {
	error_message.value = "";
	forgot_password_resource.submit(
		{ user: form.value.email },
		{
			onSuccess() {
				success_message.value = __("Password reset link has been sent to your email.");
			},
			onError(error: FrappeError) {
				error_message.value =
					error.messages?.[0] || __("Something went wrong. Please try again.");
			},
		}
	);
}

const email_link_resource = createResource({
	url: "frappe.www.login.send_login_link",
});

function handleEmailLink() {
	error_message.value = "";
	email_link_resource.submit(
		{ email: form.value.email },
		{
			onSuccess() {
				success_message.value = __("Login link has been sent to your email.");
			},
			onError(error: FrappeError) {
				error_message.value =
					error.messages?.[0] || __("Something went wrong. Please try again.");
			},
		}
	);
}

watch(is_open, (value) => {
	if (value) {
		login_context_resource.fetch({ redirect_to: window.location.href });
	}
});
</script>
