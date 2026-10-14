<script setup lang="ts">
import { Avatar, Button, Dropdown, resolvedColorScheme, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import LanguageSwitcher from "@/components/LanguageSwitcher.vue"
import SiteNavLinks from "@/components/SiteNavLinks.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { userResource } from "@/data/user"

const router = useRouter()
const { open: openLoginDialog } = useLoginDialog()
const { setColorScheme } = useColorScheme()

const toggleTheme = () => setColorScheme(resolvedColorScheme() === "dark" ? "light" : "dark")

// Website Settings' navbar fields, as the Buzz Navbar web template renders them.
const navbar = computed(() => userResource.data?.navbar)
const startLinks = computed(() => navbar.value?.links.filter((link) => !link.right) ?? [])
const endLinks = computed(() => navbar.value?.links.filter((link) => link.right) ?? [])

const menu = computed(() => [
	{
		group: session.fullName || session.user || "",
		options: [
			{ label: __("Dashboard"), icon: "lucide-layout-dashboard", onClick: () => router.push("/") },
			{
				label: __("Log Out"),
				icon: "lucide-log-out",
				disabled: session.logout.loading,
				onClick: () => session.logout.submit(),
			},
		],
	},
])
</script>

<template>
	<header class="mx-auto flex max-w-4xl items-center justify-between gap-4 p-4">
		<div class="flex min-w-0 items-center gap-4">
			<a href="/" aria-label="Home">
				<img
					v-if="userResource.data?.brand_image"
					class="h-6 contrast-100 brightness-100 invert-[0.8] dark:invert-0"
					:src="userResource.data.brand_image"
					alt=""
				/>
				<BuzzLogo v-else class="h-7 w-9 text-ink-gray-9" />
			</a>
			<SiteNavLinks :links="startLinks" align="start" />
		</div>
		<div class="flex items-center gap-2">
			<SiteNavLinks :links="endLinks" align="end" />
			<!-- A placeholder until the command palette exists. -->
			<Button v-if="navbar?.show_search" variant="outline" size="md" :aria-label="__('Search')">
				<template #prefix><span class="lucide-search size-4" aria-hidden="true" /></template>
				<span class="hidden sm:inline">{{ __("Search") }}</span>
				<kbd class="hidden rounded border px-1 text-xs text-ink-gray-5 sm:inline">⌘K</kbd>
			</Button>
			<a
				v-if="navbar?.call_to_action && navbar.call_to_action_url"
				:href="navbar.call_to_action_url"
				class="inline-flex h-8 items-center rounded-4 bg-surface-gray-10 px-2.5 text-base-medium text-ink-base transition-colors hover:bg-surface-gray-9 active:bg-surface-gray-8 focus-visible:outline-none focus-visible:focus-ring"
			>
				{{ __(navbar.call_to_action) }}
			</a>
			<Button variant="ghost" size="md" :aria-label="__('Toggle dark mode')" @click="toggleTheme">
				<span class="lucide-sun hidden size-4 dark:block" aria-hidden="true" />
				<span class="lucide-moon size-4 dark:hidden" aria-hidden="true" />
			</Button>
			<LanguageSwitcher v-if="navbar?.show_language_picker" />
			<Dropdown v-if="session.isLoggedIn" :options="menu" align="end">
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
	</header>
</template>
