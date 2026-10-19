<template>
	<Dialog v-model="is_open" size="md" @after-leave="view = 'login'">
		<template #title>
			<h3 class="text-2xl-semibold text-ink-gray-9">
				{{ view_title }}
			</h3>
		</template>
		<LoginForm v-model:view="view" />
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui"
import { computed, ref } from "vue"

import LoginForm, { type LoginView } from "@/components/LoginForm.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"

const { is_open } = useLoginDialog()
const view = ref<LoginView>("login")

const view_title = computed(() => {
	const titles = {
		login: __("Login to Continue"),
		signup: __("Create Account"),
		"forgot-password": __("Forgot Password"),
		"email-link": __("Login with Email Link"),
	}
	return titles[view.value] || __("Login")
})
</script>
