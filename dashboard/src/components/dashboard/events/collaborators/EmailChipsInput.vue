<script setup lang="ts">
import { Badge, Icon } from "frappe-ui"
import { ref } from "vue"

const SEPARATOR = /[\s,;]+/

const emails = defineModel<string[]>({ required: true })
const draft = defineModel<string>("draft", { required: true })
// `rejected` says why an address cannot be invited, or "" when it can.
defineProps<{ id: string; rejected: (email: string) => string }>()

const input = ref<HTMLInputElement>()

function add(text: string) {
	const byAddress = new Map(emails.value.map((email) => [email.toLowerCase(), email]))
	for (const email of text.split(SEPARATOR).filter(Boolean)) {
		if (!byAddress.has(email.toLowerCase())) byAddress.set(email.toLowerCase(), email)
	}
	emails.value = [...byAddress.values()]
	draft.value = ""
}

function remove(index: number) {
	emails.value = emails.value.filter((_, position) => position !== index)
	input.value?.focus()
}

function onInput() {
	if (/[,;\s]$/.test(draft.value)) add(draft.value)
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "Enter" && draft.value.trim()) {
		event.preventDefault()
		add(draft.value)
	} else if (event.key === "Backspace" && !draft.value && emails.value.length) {
		emails.value = emails.value.slice(0, -1)
	}
}

function onPaste(event: ClipboardEvent) {
	const text = event.clipboardData?.getData("text") ?? ""
	if (!SEPARATOR.test(text.trim())) return
	event.preventDefault()
	add(text)
}

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
	<!-- The whole field takes the click, so the chips never leave a dead zone. -->
	<div
		class="flex min-h-8 cursor-text flex-wrap items-center gap-1 rounded-4 bg-surface-gray-2 p-1 transition-[background-color,box-shadow] duration-150 ease-out focus-within:bg-surface-elevation-2 focus-within:ring-2 focus-within:ring-outline-gray-3 hover:bg-surface-gray-3 focus-within:hover:bg-surface-elevation-2 motion-reduce:transition-none"
		@click="input?.focus()"
	>
		<Badge
			v-for="(email, index) in emails"
			:key="email"
			:title="rejected(email)"
			class="email-chip"
			size="lg"
			variant="outline"
			:theme="rejected(email) ? 'red' : 'gray'"
			:label="email"
		>
			<template #suffix>
				<button
					type="button"
					class="inline-flex size-4 items-center justify-center rounded-1 opacity-70 hover:opacity-100"
					:aria-label="__('Remove {0}', [email])"
					@click.stop="remove(index)"
				>
					<Icon icon="lucide-x" class="size-3" aria-hidden="true" />
				</button>
			</template>
		</Badge>
		<input
			:id="id"
			ref="input"
			v-model="draft"
			type="text"
			inputmode="email"
			autocomplete="off"
			class="h-6 min-w-32 flex-1 border-0 bg-transparent px-1.5 py-0 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
			:placeholder="emails.length ? __('Add another…') : 'name@company.com'"
			@input="onInput"
			@keydown="onKeydown"
			@paste="onPaste"
			@blur="draft.trim() && add(draft)"
		/>
	</div>
</template>

<style scoped>
.email-chip {
	animation: chip-in 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes chip-in {
	from {
		opacity: 0;
		transform: scale(0.9);
	}
}

@media (prefers-reduced-motion: reduce) {
	.email-chip {
		animation: none;
	}
}
</style>
