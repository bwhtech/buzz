<script setup lang="ts">
import { Avatar, Button, Dropdown, type DropdownOptions, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import LanguageSwitcher from "@/components/LanguageSwitcher.vue"
import SiteNavLinks from "@/components/SiteNavLinks.vue"
import { useLanguageMenu } from "@/composables/useLanguageMenu"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { mobileMenu } from "@/utils/navbar"

const router = useRouter()
const { open: openLoginDialog } = useLoginDialog()
const { resolvedColorScheme, setColorScheme } = useColorScheme()
const { options: languageOptions } = useLanguageMenu()

const isDark = computed(() => resolvedColorScheme.value === "dark")
const setDark = (dark: boolean) => setColorScheme(dark ? "dark" : "light")

// Website Settings' navbar fields and Buzz Settings' logos, as the Buzz Navbar web template renders them.
const brand = computed(() => userResource.data?.brand)
const navbar = computed(() => userResource.data?.navbar)
const startLinks = computed(() => navbar.value?.links.filter((link) => !link.right) ?? [])
const endLinks = computed(() => navbar.value?.links.filter((link) => link.right) ?? [])

const accountOptions = computed(() => [
	{ label: __("Dashboard"), icon: "lucide-layout-dashboard", onClick: () => router.push("/") },
	{
		label: __("Log Out"),
		icon: "lucide-log-out",
		disabled: session.logout.loading,
		onClick: () => session.logout.submit(),
	},
])
const accountMenu = computed(() => [
	{ group: session.fullName || session.user || "", options: accountOptions.value },
])

// Small screens: one menu holds the links, account and preferences.
const mobileOptions = computed((): DropdownOptions => {
	const navbarValue = navbar.value
	if (!navbarValue) return []
	const [links, ...linkGroups] = mobileMenu(navbarValue.links)
	const cta = navbarValue.call_to_action_url
		? [
				{
					label: __(navbarValue.call_to_action || ""),
					onClick: () => window.location.assign(navbarValue.call_to_action_url ?? "/"),
				},
			]
		: []
	const login =
		!session.isLoggedIn && navbarValue.show_login
			? [{ label: __("Log In"), icon: "lucide-log-in", onClick: () => openLoginDialog() }]
			: []
	const preferences = [
		{
			label: __("Dark mode"),
			icon: "lucide-moon",
			switch: true as const,
			switchValue: isDark.value,
			onClick: setDark,
		},
		...(navbarValue.show_language_picker
			? [{ label: __("Language"), icon: "lucide-globe", submenu: languageOptions.value }]
			: []),
	]
	return [
		{ ...links, options: [...links.options, ...cta] },
		...linkGroups,
		session.isLoggedIn ? accountMenu.value[0] : { group: "", hideLabel: true, options: login },
		{ group: "", hideLabel: true, options: preferences },
	].filter((group) => group.options.length) as DropdownOptions
})
</script>

<template>
	<header class="mx-auto flex max-w-4xl items-center justify-between gap-4 p-4">
		<div class="flex min-w-0 items-center gap-4">
			<a href="/" :aria-label="brand?.name ?? __('Home')">
				<BuzzLogo v-if="!brand || brand.is_default" class="h-7 w-9 text-ink-gray-9" />
				<template v-else>
					<img class="h-6 w-auto dark:hidden" :src="brand.logo" alt="" />
					<img class="hidden h-6 w-auto dark:block" :src="brand.logo_dark || brand.logo" alt="" />
				</template>
			</a>
			<SiteNavLinks :links="startLinks" align="start" />
		</div>
		<div class="hidden items-center gap-2 sm:flex">
			<SiteNavLinks :links="endLinks" align="end" />
			<a
				v-if="navbar?.call_to_action && navbar.call_to_action_url"
				:href="navbar.call_to_action_url"
				class="inline-flex h-8 items-center rounded-4 bg-surface-gray-10 px-2.5 text-base-medium text-ink-base transition-colors hover:bg-surface-gray-9 active:bg-surface-gray-8 focus-visible:outline-none focus-visible:focus-ring"
			>
				{{ __(navbar.call_to_action) }}
			</a>
			<Button
				variant="ghost"
				size="md"
				:aria-label="__('Toggle dark mode')"
				@click="setDark(!isDark)"
			>
				<span class="lucide-sun hidden size-4 dark:block" aria-hidden="true" />
				<span class="lucide-moon size-4 dark:hidden" aria-hidden="true" />
			</Button>
			<LanguageSwitcher v-if="navbar?.show_language_picker" />
			<Dropdown v-if="session.isLoggedIn" :options="accountMenu" align="end">
				<button
					type="button"
					class="rounded-full transition-transform duration-150 ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:focus-ring motion-reduce:transition-none"
					:aria-label="__('Account menu')"
				>
					<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
				</button>
			</Dropdown>
			<Button
				v-else-if="navbar?.show_login"
				variant="ghost"
				size="md"
				:label="__('Log In')"
				@click="openLoginDialog"
			/>
		</div>
		<div v-if="mobileOptions.length" class="sm:hidden">
			<Dropdown :options="mobileOptions" align="end">
				<button
					v-if="session.isLoggedIn"
					type="button"
					class="rounded-full focus-visible:outline-none focus-visible:focus-ring"
					:aria-label="__('Menu')"
				>
					<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
				</button>
				<Button v-else variant="ghost" size="md" icon="lucide-menu" :aria-label="__('Menu')" />
			</Dropdown>
		</div>
	</header>
</template>
