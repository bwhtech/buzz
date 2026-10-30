<script setup lang="ts">
import { Avatar, BottomSheet, ItemListRow } from "frappe-ui"
import { ref } from "vue"
import { RouterLink, useRoute } from "vue-router"

import { session } from "@/data/session"
import type { ManagerNavItem } from "@/utils/managerNavigation"

defineProps<{ items: ManagerNavItem[] }>()
const emit = defineEmits<{ account: [] }>()
const open = defineModel<boolean>("open", { default: false })

const route = useRoute()

// The account sheet waits for this one to leave, so the two never stack.
const accountRequested = ref(false)

function requestAccount() {
	accountRequested.value = true
	open.value = false
}

function afterLeave() {
	if (!accountRequested.value) return
	accountRequested.value = false
	emit("account")
}
</script>

<template>
	<BottomSheet v-model:open="open" @after-leave="afterLeave">
		<div class="px-2 pb-6">
			<!-- A native button around the row: as="button" resolves to frappe-ui's global Button. -->
			<button class="w-full rounded-4 text-left" @click="requestAccount">
				<ItemListRow size="lg" class="hover:bg-surface-gray-2">
					<template #prefix>
						<Avatar :image="session.userImage ?? undefined" :label="session.fullName" size="lg" />
					</template>
					<p class="truncate text-base font-medium text-ink-gray-9">{{ session.fullName }}</p>
					<p class="truncate text-sm text-ink-gray-5">{{ session.user }}</p>
					<template #suffix>
						<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</ItemListRow>
			</button>

			<div class="my-2 border-t border-outline-gray-1" />

			<ItemListRow
				v-for="item in items"
				:key="item.to"
				:as="RouterLink"
				:to="item.to"
				size="lg"
				:active="route.path === item.to"
				@click="open = false"
			>
				<template #prefix>
					<span :class="item.icon" class="size-5 text-ink-gray-6" aria-hidden="true" />
				</template>
				<span class="text-base text-ink-gray-8">{{ __(item.label) }}</span>
			</ItemListRow>
		</div>
	</BottomSheet>
</template>
