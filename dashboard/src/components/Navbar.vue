<template>
	<div class="border-b">
		<nav class="flex items-center justify-between gap-4 p-4 max-w-4xl mx-auto">
			<a href="/">
				<img
					class="h-6 contrast-100 brightness-100 invert-[0.8] dark:invert-0"
					v-if="userResource?.data?.brand_image"
					:src="userResource.data.brand_image"
				/>
				<BuzzLogo v-else class="w-9 h-7 text-ink-gray-9" />
			</a>
			<div class="flex items-center gap-2">
				<Button variant="ghost" size="md" @click="toggleTheme">
					<LucideSun class="hidden w-4 h-4 dark:block" />
					<LucideMoon class="w-4 h-4 dark:hidden" />
				</Button>
				<LanguageSwitcher />
				<Button
					v-if="session.isLoggedIn"
					:loading="session.logout.loading"
					@click="session.logout.submit"
					icon-right="lucide-log-out"
					variant="ghost"
					size="md"
				>
					{{ __("Log Out") }}
				</Button>
				<Button
					v-else
					@click="openLoginDialog"
					icon-right="lucide-log-in"
					variant="ghost"
					size="md"
				>
					{{ __("Log In") }}
				</Button>
			</div>
		</nav>
	</div>
</template>

<script setup lang="ts">
import { resolvedColorScheme, useColorScheme } from "frappe-ui"
import LucideMoon from "~icons/lucide/moon"
import LucideSun from "~icons/lucide/sun"

import { useLoginDialog } from "@/composables/useLoginDialog"
import { userResource } from "@/data/user"

import { session } from "../data/session"
import BuzzLogo from "./common/BuzzLogo.vue"
import LanguageSwitcher from "./LanguageSwitcher.vue"

const { open: openLoginDialog } = useLoginDialog()
const { setColorScheme } = useColorScheme()

function toggleTheme() {
	setColorScheme(resolvedColorScheme() === "dark" ? "light" : "dark")
}
</script>
