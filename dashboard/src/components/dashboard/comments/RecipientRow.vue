<script setup lang="ts">
import { ref } from "vue"

defineProps<{
	label: string
	// Recipients the row shows but does not let you remove, such as a proposal's speakers.
	fixed?: string[]
}>()

const addresses = defineModel<string[]>({ default: () => [] })
const draft = ref("")

function add() {
	const address = draft.value.trim().replace(/,$/, "")
	if (address && !addresses.value.includes(address)) addresses.value = [...addresses.value, address]
	draft.value = ""
}

function remove(index: number) {
	addresses.value = addresses.value.filter((_, position) => position !== index)
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "Enter" || event.key === ",") {
		event.preventDefault()
		add()
	} else if (event.key === "Backspace" && !draft.value && addresses.value.length) {
		remove(addresses.value.length - 1)
	}
}
</script>

<template>
	<div class="flex min-h-[30px] flex-wrap items-center gap-1.5 pr-2.5 pl-3">
		<span class="w-[30px] shrink-0 text-sm text-ink-gray-5">{{ label }}</span>
		<span
			v-for="name in fixed"
			:key="name"
			class="inline-flex h-[22px] items-center rounded-3 bg-surface-gray-2 px-2 text-sm text-ink-gray-8"
		>
			{{ name }}
		</span>
		<span
			v-for="(address, index) in addresses"
			:key="address"
			class="inline-flex h-[22px] items-center gap-0.5 rounded-3 bg-surface-gray-2 pr-0.5 pl-2 text-sm text-ink-gray-8"
		>
			{{ address }}
			<button
				class="flex rounded-1 p-0.5 text-ink-gray-5 hover:text-ink-gray-9"
				:aria-label="`Remove ${address}`"
				@click="remove(index)"
			>
				<span class="lucide-x size-3" aria-hidden="true" />
			</button>
		</span>
		<input
			v-if="!fixed"
			v-model="draft"
			type="email"
			class="h-[26px] min-w-[100px] flex-1 border-none bg-transparent p-0 text-sm text-ink-gray-8 outline-none focus:ring-0"
			:placeholder="addresses.length ? '' : 'Add email'"
			:aria-label="`${label} recipients`"
			@keydown="onKeydown"
			@blur="add"
		/>
		<span v-else class="flex-1" />
		<slot />
	</div>
</template>
