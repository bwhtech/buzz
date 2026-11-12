<script setup lang="ts">
import { useRoute, useRouter } from "vue-router"

const OPTIONS = [
	{ label: "Demo", value: undefined },
	{ label: "Worst case", value: "worst" },
	{ label: "Empty", value: "empty" },
	{ label: "One", value: "one" },
	{ label: "Many", value: "many" },
]

const route = useRoute()
const router = useRouter()

// Fixtures are applied when data is fetched, so a reload is the simplest refresh.
async function select(value?: string) {
	await router.replace({ query: { ...route.query, data: value, page: undefined } })
	window.location.reload()
}
</script>

<template>
	<div
		role="group"
		aria-label="Data set"
		class="fixed bottom-16 left-1/2 md:bottom-3 z-[1000] flex -translate-x-1/2 gap-0.5 rounded-lg bg-gray-200 p-0.5 font-sans text-xs"
	>
		<button
			v-for="option in OPTIONS"
			:key="option.label"
			type="button"
			class="whitespace-nowrap rounded-md px-2.5 py-1 text-gray-700"
			:class="
				(route.query.data ?? undefined) === option.value &&
				'bg-white font-medium text-gray-900 shadow-sm'
			"
			@click="select(option.value)"
		>
			{{ option.label }}
		</button>
	</div>
</template>
