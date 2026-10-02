<script setup lang="ts">
import { onMounted, watch } from "vue"
import { useRoute } from "vue-router"

import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"

type EmbedState = "ready" | "close" | "success"

const route = useRoute()
const { is_open, open: openLogin } = useLoginDialog()

function notifyParent(state: EmbedState) {
	window.parent.postMessage({ type: "buzz-login", state }, window.location.origin)
}

function matchParentTheme() {
	const mode = route.query.mode === "light" ? "light" : "dark"
	const root = document.documentElement
	root.dataset.theme = mode
	root.style.colorScheme = mode
	root.style.background = "transparent"
	document.body.style.background = "transparent"
}

watch(is_open, (open) => {
	if (!open) notifyParent(session.isLoggedIn ? "success" : "close")
})

onMounted(() => {
	matchParentTheme()
	if (session.isLoggedIn) {
		notifyParent("success")
		return
	}
	openLogin()
	notifyParent("ready")
})
</script>

<template>
	<div />
</template>
