<script setup lang="ts">
import { Avatar, Button, Dropdown, resolvedColorScheme, useColorScheme } from "frappe-ui"
import { computed } from "vue"
import { useRouter } from "vue-router"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { userResource } from "@/data/user"

const router = useRouter()
const { open: openLoginDialog } = useLoginDialog()
const { setColorScheme } = useColorScheme()

const toggleTheme = () => setColorScheme(resolvedColorScheme() === "dark" ? "light" : "dark")

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
		<a href="/" aria-label="Home">
			<img
				v-if="userResource.data?.brand_image"
				class="h-6 contrast-100 brightness-100 invert-[0.8] dark:invert-0"
				:src="userResource.data.brand_image"
				alt=""
			/>
			<BuzzLogo v-else class="h-7 w-9 text-ink-gray-9" />
		</a>
		<nav class="flex items-center gap-3">
			<Button variant="ghost" size="md" :aria-label="__('Toggle dark mode')" @click="toggleTheme">
				<span class="lucide-sun hidden size-4 dark:block" aria-hidden="true" />
				<span class="lucide-moon size-4 dark:hidden" aria-hidden="true" />
			</Button>
			<Dropdown v-if="session.isLoggedIn" :options="menu" align="end">
				<button
					type="button"
					class="rounded-full transition-transform duration-150 ease-out active:scale-[0.97] focus-visible:outline-none focus-visible:focus-ring motion-reduce:transition-none"
					:aria-label="__('Account menu')"
				>
					<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
				</button>
			</Dropdown>
			<Button v-else variant="ghost" size="md" :label="__('Log In')" @click="openLoginDialog" />
		</nav>
	</header>
</template>
