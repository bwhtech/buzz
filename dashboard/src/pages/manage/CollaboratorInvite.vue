<script setup lang="ts">
import { Button, ErrorMessage, LoadingIndicator } from "frappe-ui"
import { onMounted, ref } from "vue"
import { useRoute } from "vue-router"

import { useAcceptCollaboratorInvite } from "@/data/collaborators"
import { serverErrorMessage } from "@/utils/serverError"

const route = useRoute()
const acceptInvite = useAcceptCollaboratorInvite()
const errorMessage = ref("")
const needsLogin = ref(false)

// The server names this error by class; any other failure just shows its message.
const LOGIN_REQUIRED = "CollaboratorLoginRequired"

onMounted(async () => {
	try {
		const result = await acceptInvite.submit({ key: String(route.query.key ?? "") })
		// A full load: the session may have just been created, and the redirect may leave /b.
		window.location.assign(result?.redirect_to ?? "/b/manage")
	} catch (error) {
		needsLogin.value = String(acceptInvite.error?.type ?? "").includes(LOGIN_REQUIRED)
		errorMessage.value = serverErrorMessage(acceptInvite.error ?? error)
	}
})

function logIn() {
	window.location.assign(
		`/b/login?redirect-to=${encodeURIComponent(window.location.pathname + window.location.search)}`,
	)
}
</script>

<template>
	<div class="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
		<template v-if="errorMessage">
			<span class="lucide-mail-warning size-12 text-ink-gray-5" />
			<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Invitation not accepted") }}</h2>
			<ErrorMessage :message="errorMessage" />
			<Button v-if="needsLogin" variant="solid" :label="__('Log in')" @click="logIn" />
		</template>
		<template v-else>
			<LoadingIndicator class="size-6 text-ink-gray-5" />
			<p class="text-base text-ink-gray-6">{{ __("Accepting your invitation") }}</p>
		</template>
	</div>
</template>
