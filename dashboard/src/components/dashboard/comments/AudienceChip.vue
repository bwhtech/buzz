<script setup lang="ts">
import { onClickOutside } from "@vueuse/core"
import { Avatar } from "frappe-ui"
import { computed, ref } from "vue"

export interface Recipient {
	name: string
	email: string
}

const props = defineProps<{ recipients: Recipient[]; recipientsLabel: string }>()

// True means the note goes out by email instead of staying with the team.
const toRecipients = defineModel<boolean>({ required: true })

const open = ref(false)
const root = ref<HTMLElement>()
onClickOutside(root, () => (open.value = false))

const firstNames = computed(() =>
	props.recipients.map((person) => person.name.split(" ")[0]).join(" and "),
)

const options = computed(() => [
	{ value: false, label: "Team only", hint: "Only your team sees this note", icon: "lucide-lock" },
	{
		value: true,
		label: `Email ${props.recipientsLabel}`,
		hint: `Sent to ${firstNames.value} by email`,
		icon: "lucide-mail",
	},
])

function choose(value: boolean) {
	toRecipients.value = value
	open.value = false
}
</script>

<template>
	<div ref="root" class="relative">
		<button
			type="button"
			class="chip flex h-7 items-center gap-1.5 rounded-full px-2.5 text-sm transition-colors duration-150"
			:class="
				toRecipients
					? 'bg-surface-blue-1 text-ink-blue-6'
					: 'text-ink-gray-6 hover:bg-surface-gray-2'
			"
			:aria-expanded="open"
			aria-haspopup="menu"
			@click="open = !open"
		>
			<span
				:class="toRecipients ? 'lucide-mail' : 'lucide-lock'"
				class="size-3.5"
				aria-hidden="true"
			/>
			<template v-if="toRecipients">
				Email {{ recipientsLabel }}
				<span class="ml-0.5 flex -space-x-1.5">
					<Avatar
						v-for="person in recipients"
						:key="person.email"
						size="xs"
						:label="person.name"
						class="ring-2 ring-surface-blue-1"
					/>
				</span>
			</template>
			<template v-else>Team only</template>
			<span class="lucide-chevron-down size-3 opacity-60" aria-hidden="true" />
		</button>

		<div
			v-if="open"
			class="menu absolute bottom-full left-0 z-20 mb-2 w-64 rounded-8 bg-surface-elevation-3 p-1 shadow-xl ring-1 ring-outline-gray-1"
			role="menu"
		>
			<button
				v-for="option in options"
				:key="option.label"
				type="button"
				role="menuitemradio"
				:aria-checked="toRecipients === option.value"
				class="flex w-full items-start gap-2.5 rounded-6 px-2 py-2 text-left hover:bg-surface-gray-2"
				@click="choose(option.value)"
			>
				<span :class="option.icon" class="mt-0.5 size-4 text-ink-gray-6" aria-hidden="true" />
				<span class="min-w-0 flex-1">
					<span class="block text-base text-ink-gray-8">{{ option.label }}</span>
					<span class="block text-sm text-ink-gray-5">{{ option.hint }}</span>
				</span>
				<span
					v-if="toRecipients === option.value"
					class="lucide-check mt-0.5 size-4 text-ink-gray-7"
					aria-hidden="true"
				/>
			</button>
		</div>
	</div>
</template>

<style scoped>
.chip:active {
	transform: scale(0.97);
}

.menu {
	transform-origin: bottom left;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.menu {
		opacity: 0;
		transform: scale(0.97);
	}
}
</style>
