<script setup lang="ts">
import { Avatar } from "frappe-ui"
import { computed } from "vue"

interface GroupUser {
	full_name?: string | null
	user?: string
	user_image?: string | null
}

const props = withDefaults(defineProps<{ users: GroupUser[]; max?: number }>(), { max: 3 })

// A cached row from before members shipped still carries no list.
const all = computed(() => props.users ?? [])

const shown = computed(() => all.value.slice(0, props.max))

const count = computed(() => all.value.length)

const label = computed(() =>
	count.value === 1 ? __("1 member") : __("{0} members", [String(count.value)]),
)
</script>

<template>
	<div class="flex items-center gap-2">
		<!-- Overlap needs a margin; the row's gap alone would spread the stack apart. -->
		<div v-if="shown.length" class="flex shrink-0 -space-x-1.5" aria-hidden="true">
			<Avatar
				v-for="user in shown"
				:key="user.user ?? user.full_name ?? ''"
				size="sm"
				:image="user.user_image ?? undefined"
				:label="user.full_name ?? user.user ?? ''"
				class="ring-2 ring-surface-white"
			/>
		</div>
		<span class="truncate text-base text-ink-gray-6">{{ label }}</span>
	</div>
</template>
