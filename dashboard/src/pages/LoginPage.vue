<script setup lang="ts">
import { onMounted, watch } from "vue"
import { useRoute } from "vue-router"

import LoginRequired from "@/components/LoginRequired.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { resolveLoginRedirect } from "@/utils/loginRedirect"

const route = useRoute()
const { open: openLogin } = useLoginDialog()

watch(
	() => session.isLoggedIn,
	(isLoggedIn) => {
		if (isLoggedIn) {
			window.location.replace(
				resolveLoginRedirect(route.query["redirect-to"], window.location.origin),
			)
		}
	},
	{ immediate: true },
)

onMounted(() => {
	if (!session.isLoggedIn) openLogin()
})
</script>

<template>
	<LoginRequired v-if="!session.isLoggedIn" />
</template>
