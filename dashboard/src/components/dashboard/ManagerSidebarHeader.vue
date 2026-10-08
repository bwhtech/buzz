<script setup lang="ts">
import { Avatar, Tooltip, sidebarCollapsedKey } from "frappe-ui"
import { computed, inject } from "vue"
import { useRoute, useRouter } from "vue-router"

import type { Workspace } from "@/utils/managerNavigation"

const props = defineProps<{ workspace?: Workspace }>()

const route = useRoute()
const router = useRouter()
const isCollapsed = inject(
	sidebarCollapsedKey,
	computed(() => false),
)

// Never falls back to the id: swapping a hash for the title reads as a glitch.
const name = computed(() => props.workspace?.title ?? "")

const isCreatingEvent = computed(() => route.name === "create-event")

const goToEvents = () => router.push("/manage/events")

// Deep links have nothing to go back to, so the events list stands in.
const goBack = () => (window.history.state?.back ? router.back() : goToEvents())
</script>

<template>
	<Tooltip
		v-if="isCreatingEvent"
		class="w-full"
		text="Go back"
		side="right"
		:disabled="!isCollapsed"
	>
		<button
			aria-label="Go back"
			class="group flex h-12 w-full items-center gap-1.5 rounded-4 px-1 transition duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98] focus-visible:outline-none focus-visible:focus-ring"
			@click="goBack"
		>
			<span
				class="lucide-chevron-left size-4 shrink-0 text-ink-gray-5 transition duration-150 ease-out group-hover:-translate-x-0.5 group-hover:text-ink-gray-8"
			/>
			<span v-if="!isCollapsed" class="truncate text-base font-medium text-ink-gray-8">
				Go back
			</span>
		</button>
	</Tooltip>

	<!-- Identity and the way home; the account menu sits in the sidebar footer. -->
	<Tooltip v-else-if="!workspace" class="w-full" text="Buzz" side="right" :disabled="!isCollapsed">
		<router-link
			to="/manage"
			class="flex h-12 w-full items-center gap-2 rounded-4 px-1.5 transition-[background-color,transform] duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98] focus-visible:outline-none focus-visible:focus-ring"
		>
			<Avatar
				image="/assets/buzz/images/buzz-logo-rounded.png"
				label="Buzz"
				size="lg"
				shape="square"
			/>
			<span v-if="!isCollapsed" class="flex-1 truncate text-base font-medium text-ink-gray-8">
				Buzz
			</span>
		</router-link>
	</Tooltip>

	<Tooltip v-else class="w-full" :text="workspace.back.label" side="right" :disabled="!isCollapsed">
		<button
			:aria-label="workspace.back.label"
			class="group flex h-12 w-full items-center gap-1.5 rounded-4 px-1 transition duration-150 ease-out hover:bg-surface-gray-2 active:scale-[0.98] focus-visible:outline-none focus-visible:focus-ring"
			@click="router.push(workspace.back.to)"
		>
			<span
				class="lucide-chevron-left size-4 shrink-0 text-ink-gray-5 transition duration-150 ease-out group-hover:-translate-x-0.5 group-hover:text-ink-gray-8"
			/>
			<span
				v-if="workspace.icon"
				class="flex size-7 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-7 transition-colors duration-150 ease-out group-hover:bg-surface-gray-3"
			>
				<span class="size-4" :class="workspace.icon" />
			</span>
			<Avatar
				v-else
				class="shrink-0"
				shape="square"
				size="md"
				:image="workspace.image ?? undefined"
				:label="name"
			/>
			<span v-if="!isCollapsed" class="flex min-w-0 flex-col text-left leading-tight">
				<span
					class="truncate text-base font-medium text-ink-gray-8 transition-opacity duration-150 ease-out"
					:class="{ 'opacity-0': !name }"
					:title="name"
				>
					{{ name || "\u00a0" }}
				</span>
				<span class="truncate text-xs text-ink-gray-5">{{ workspace.subtitle }}</span>
			</span>
		</button>
	</Tooltip>
</template>
