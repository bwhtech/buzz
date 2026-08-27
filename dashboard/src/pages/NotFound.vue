<script setup lang="ts">
import { Button } from "frappe-ui"
import { useRouter } from "vue-router"

const router = useRouter()
</script>

<template>
	<div class="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
		<span class="lucide-file-question size-12 text-ink-gray-5" />
		<h2 class="text-xl font-semibold text-ink-gray-8">Page not found</h2>
		<p class="text-base text-ink-gray-6">
			This page doesn't exist, or you don't have access to it.
		</p>
		<Button class="mt-2" @click="router.replace('/')">Go to dashboard</Button>
	</div>
</template>
