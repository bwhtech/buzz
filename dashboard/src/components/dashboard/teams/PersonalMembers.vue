<script setup lang="ts">
import { Avatar, Button, Tooltip } from "frappe-ui"

import { session } from "@/data/session"
</script>

<template>
	<div class="flex flex-col items-center gap-6 py-10 text-center">
		<div class="flex flex-col items-center gap-3">
			<div class="flex items-center -space-x-3" aria-hidden="true">
				<Avatar
					size="3xl"
					class="relative z-10"
					:image="session.userImage ?? undefined"
					:label="session.fullName"
				/>
				<span
					v-for="seat in 3"
					:key="seat"
					class="grid size-12 place-items-center rounded-full border border-dashed border-outline-gray-3 bg-surface-white"
				>
					<span class="lucide-lock size-4 text-ink-gray-4" />
				</span>
			</div>
			<p class="text-sm text-ink-gray-5">
				<span class="font-medium text-ink-gray-8">{{ session.fullName }}</span>
				({{ __("You") }}) · {{ __("Owner") }}
			</p>
		</div>

		<div class="flex max-w-md flex-col gap-2">
			<h2 class="text-xl font-semibold text-ink-gray-9">
				{{ __("Your personal calendar is just for you") }}
			</h2>
			<p class="text-p-base text-ink-gray-5">
				{{
					__(
						"You can't add admins or other members here. To run events with others, create a community.",
					)
				}}
			</p>
		</div>

		<div class="flex flex-wrap items-center justify-center gap-2">
			<Tooltip
				:text="__('You can\'t add admins or other members here. Create a community instead.')"
			>
				<span>
					<Button variant="subtle" icon-left="lucide-plus" :label="__('Add member')" disabled />
				</span>
			</Tooltip>
			<Button variant="solid" :label="__('Create a community')" href="/community?create" />
		</div>
	</div>
</template>
