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
					<LucideSun v-if="userTheme === 'dark'" class="w-4 h-4" />
					<LucideMoon v-else class="w-4 h-4" />
				</Button>
				<LanguageSwitcher />
				<Button
					v-if="session.isLoggedIn"
					:loading="session.logout.loading"
					@click="session.logout.submit"
					icon-right="log-out"
					variant="ghost"
					size="md"
				>
					{{ __("Log Out") }}
				</Button>
				<Button
					v-else
					@click="openLoginDialog"
					icon-right="log-in"
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
import { userResource } from "@/data/user";
import LucideMoon from "~icons/lucide/moon";
import LucideSun from "~icons/lucide/sun";
import { session } from "../data/session";
import LanguageSwitcher from "./LanguageSwitcher.vue";
import BuzzLogo from "./common/BuzzLogo.vue";

import { useLoginDialog } from "@/composables/useLoginDialog";
import { useStorage } from "@vueuse/core";
import { onMounted } from "vue";

const { open: openLoginDialog } = useLoginDialog();
const userTheme = useStorage("user-theme", "dark");

onMounted(() => {
	document.documentElement.setAttribute("data-theme", userTheme.value);
});

function toggleTheme() {
	const currentTheme = userTheme.value;
	const newTheme = currentTheme === "dark" ? "light" : "dark";
	document.documentElement.setAttribute("data-theme", newTheme);
	userTheme.value = newTheme;
}
</script>
