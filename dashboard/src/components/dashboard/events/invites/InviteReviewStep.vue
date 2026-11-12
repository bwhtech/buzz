<script setup lang="ts">
// Review: a guest list with names to fill in. The alert appears only after Add directly fails.
import { Alert, Avatar, Button, Select, TextInput } from "frappe-ui"
import {
	List,
	ListCell,
	ListGroup,
	ListHeader,
	ListHeaderCell,
	ListRow,
	ListRows,
} from "frappe-ui/list"
import { computed, ref } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

import { displayName, type Invitee, needsName, type TierOption } from "./invites"

const invitees = defineModel<Invitee[]>({ required: true })
const props = defineProps<{ tiers: TierOption[]; attempted: boolean }>()
const emit = defineEmits<{ remove: [invitee: Invitee] }>()

// On a phone the email and ticket move under the name, so the row keeps three columns.
const COLUMNS = {
	base: ["2rem", "minmax(0,1fr)", "2rem"],
	sm: ["2rem", "minmax(0,1fr)", "minmax(0,1.3fr)", "9rem", "2rem"],
}
const isMobile = useIsMobile()
const grouped = ref(false)
const onlyMissing = ref(false)
// Rows that opened without a name keep their name field, and their place in the filtered view,
// while the name is typed.
const nameless = new Set(invitees.value.filter(needsName).map((row) => row.id))

const missingCount = computed(() => invitees.value.filter(needsName).length)
const visible = computed(() =>
	onlyMissing.value ? invitees.value.filter((row) => nameless.has(row.id)) : invitees.value,
)
const groups = computed(() =>
	grouped.value ? byTicket(visible.value) : [{ key: "", rows: visible.value }],
)
const flagged = (row: Invitee) => props.attempted && needsName(row)

function byTicket(rows: Invitee[]) {
	const label = (value: string) => props.tiers.find((tier) => tier.value === value)?.label ?? value
	const keys = [...new Set(rows.map((row) => row.ticket_type))]
	return keys.map((key) => ({
		key: label(key),
		rows: rows.filter((row) => row.ticket_type === key),
	}))
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<div class="flex items-center gap-2 px-4 pt-4 sm:px-5">
			<p class="flex-1 text-p-sm text-ink-gray-6">
				{{
					onlyMissing
						? `${visible.length} of ${invitees.length} guests`
						: `${invitees.length} guests`
				}}
			</p>
			<Button
				size="sm"
				:variant="grouped ? 'subtle' : 'ghost'"
				icon-left="lucide-layers"
				label="Group"
				@click="grouped = !grouped"
			/>
		</div>

		<Transition name="alert">
			<Alert
				v-if="attempted && (missingCount || onlyMissing)"
				class="mx-4 mt-3 sm:mx-5"
				:theme="missingCount ? 'amber' : 'green'"
				:icon="missingCount ? 'lucide-user-pen' : true"
				:title="
					missingCount
						? `${missingCount} ${missingCount === 1 ? 'guest needs' : 'guests need'} a first name to add directly`
						: 'Everyone has a name'
				"
				:description="missingCount ? 'Invites work without one.' : undefined"
				:primary-action="{
					label: onlyMissing ? 'Show all' : 'Show only these',
					onClick: () => {
						onlyMissing = !onlyMissing
					},
				}"
			/>
		</Transition>

		<div class="min-h-0 flex-1 overflow-y-auto px-4 py-3 sm:px-5">
			<List :columns="COLUMNS" divider="none" class="list-row-px-2">
				<!-- The list stylesheet sets the header's display, so a class can't hide it on phones. -->
				<ListHeader v-if="!isMobile">
					<ListHeaderCell />
					<ListHeaderCell>Name</ListHeaderCell>
					<ListHeaderCell>Email</ListHeaderCell>
					<ListHeaderCell>Ticket</ListHeaderCell>
					<ListHeaderCell />
				</ListHeader>
				<ListGroup
					v-for="group in groups"
					:key="group.key"
					:label="group.key ? `${group.key} · ${group.rows.length}` : undefined"
				>
					<ListRows v-slot="{ item: row }" :items="group.rows" row-key="id">
						<ListRow
							:data-missing="flagged(row) || undefined"
							class="row group min-h-11 rounded-4"
							:class="flagged(row) && 'bg-surface-amber-2'"
						>
							<ListCell class="max-sm:self-start max-sm:pt-1.5">
								<Avatar :label="displayName(row)" size="md" />
							</ListCell>
							<ListCell class="flex-col !items-stretch gap-1 py-1.5">
								<TextInput
									v-if="nameless.has(row.id)"
									v-model="row.first_name"
									class="w-full"
									size="sm"
									placeholder="First name"
									:aria-label="`First name for ${row.email}`"
								/>
								<span v-else class="truncate text-p-sm text-ink-gray-9">{{
									displayName(row)
								}}</span>
								<span class="truncate text-p-xs text-ink-gray-5 sm:hidden">{{ row.email }}</span>
								<Select
									v-model="row.ticket_type"
									class="w-full sm:hidden"
									size="sm"
									:options="tiers"
									:aria-label="`Ticket for ${row.email}`"
								/>
							</ListCell>
							<ListCell class="truncate text-p-sm text-ink-gray-6 max-sm:hidden">
								{{ row.email }}
							</ListCell>
							<ListCell class="max-sm:hidden">
								<Select
									v-model="row.ticket_type"
									class="w-full"
									size="sm"
									:options="tiers"
									:aria-label="`Ticket for ${row.email}`"
								/>
							</ListCell>
							<ListCell class="justify-end max-sm:self-start max-sm:pt-1">
								<Button
									variant="ghost"
									size="sm"
									icon="lucide-x"
									class="transition-opacity duration-150 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:focus-visible:opacity-100"
									:label="`Remove ${row.email}`"
									@click="emit('remove', row)"
								/>
							</ListCell>
						</ListRow>
					</ListRows>
				</ListGroup>
			</List>
		</div>
	</div>
</template>

<style scoped>
.row {
	transition: background-color 150ms ease-out;
}
.alert-enter-active {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.alert-enter-from {
	opacity: 0;
	transform: translateY(-4px);
}
.alert-leave-active {
	transition: opacity 120ms ease-out;
}
.alert-leave-to {
	opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
	.alert-enter-from {
		transform: none;
	}
}
</style>
