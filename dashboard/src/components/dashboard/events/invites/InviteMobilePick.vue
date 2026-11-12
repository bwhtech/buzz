<script setup lang="ts">
// The pick step on a phone: tabs replace the rail, and a past event opens as its own page.
import { Button, LoadingText, SidebarItem, TabButtons } from "frappe-ui"
import { computed, ref } from "vue"

import InviteEmailsPane from "./InviteEmailsPane.vue"
import type { TierOption } from "./invites"
import PastEventGuests from "./PastEventGuests.vue"
import type { InviteFlow } from "./useInviteFlow"

const props = defineProps<{ flow: InviteFlow; event: string; tiers: TierOption[] }>()

const tab = ref("emails")
const openEventName = ref("")
const pastEvents = props.flow.pastEvents
const openEvent = computed(() =>
	pastEvents.data?.find((row) => String(row.name) === openEventName.value),
)
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div v-if="!openEvent" class="px-4 pt-3">
			<TabButtons
				v-model="tab"
				class="w-full [&>*]:flex-1"
				:options="[
					{ value: 'emails', label: 'Emails', iconLeft: 'lucide-at-sign' },
					{ value: 'past', label: 'Past events', iconLeft: 'lucide-calendar' },
				]"
			/>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">
			<InviteEmailsPane
				v-if="tab === 'emails'"
				:event="event"
				:selection="flow.selection"
				:tiers="tiers"
				:default-tier="flow.defaultTier.value"
			/>
			<template v-else-if="openEvent">
				<Button
					class="-ml-2 mb-2"
					variant="ghost"
					icon-left="lucide-chevron-left"
					label="Past events"
					@click="openEventName = ''"
				/>
				<PastEventGuests
					:key="openEventName"
					:event="openEventName"
					:title="openEvent.title"
					:is-selected="flow.selection.isSelected"
					@toggle="flow.toggle"
					@select-all="flow.selection.add"
				/>
			</template>
			<div v-else class="-mx-2">
				<LoadingText v-if="pastEvents.loading && !pastEvents.data" class="px-2 py-1.5" />
				<p v-else-if="!pastEvents.data?.length" class="px-2 py-1.5 text-p-sm text-ink-gray-5">
					This is your first event.
				</p>
				<SidebarItem
					v-for="row in pastEvents.data"
					:key="row.name"
					:label="row.title"
					icon="lucide-calendar"
					:on-click="() => (openEventName = String(row.name))"
				>
					<template #suffix>
						<span class="lucide-chevron-right size-4 text-ink-gray-4" aria-hidden="true" />
					</template>
				</SidebarItem>
			</div>
		</div>
	</div>
</template>
