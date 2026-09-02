<script setup lang="ts">
import { Tooltip, sidebarCollapsedKey } from "frappe-ui"
import { computed, inject } from "vue"
import { useRouter } from "vue-router"

import UserMenu from "@/components/UserMenu.vue"

const props = defineProps<{ eventId?: string; eventTitle?: string }>()

const router = useRouter()
const isCollapsed = inject(
	sidebarCollapsedKey,
	computed(() => false),
)

// Never falls back to the id: swapping a hash for the title reads as a glitch.
const name = computed(() => props.eventTitle ?? "")

const goBack = () => router.push("/manage/events")
</script>

<template>
	<UserMenu v-if="!eventId" />

	<Tooltip v-else class="w-full" text="Back to events" placement="right" :disabled="!isCollapsed">
		<button
			aria-label="Back to events"
			class="group flex h-12 w-full items-center gap-1.5 rounded-4 px-1 transition duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98] focus-visible:outline-none focus-visible:focus-ring"
			@click="goBack"
		>
			<span
				class="lucide-chevron-left size-4 shrink-0 text-ink-gray-5 transition duration-150 ease-out group-hover:-translate-x-0.5 group-hover:text-ink-gray-8"
			/>
			<span
				class="flex size-7 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-7 transition-colors duration-150 ease-out group-hover:bg-surface-gray-3"
			>
				<span class="lucide-box size-4" />
			</span>
			<span v-if="!isCollapsed" class="flex min-w-0 flex-col text-left leading-tight">
				<span
					class="truncate text-base font-medium text-ink-gray-8 transition-opacity duration-150 ease-out"
					:class="{ 'opacity-0': !name }"
					:title="name"
				>
					{{ name || "\u00a0" }}
				</span>
				<span class="truncate text-xs text-ink-gray-5">Event Workspace</span>
			</span>
		</button>
	</Tooltip>
</template>
