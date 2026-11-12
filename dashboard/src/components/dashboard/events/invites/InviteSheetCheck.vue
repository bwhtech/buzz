<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed } from "vue"

import { duplicateIds, guestCount, type Invitee, isValidEmail, type TierOption } from "./invites"

// Mirrors the sponsor import's check step: each blocker is a card with one decision.
const rows = defineModel<Invitee[]>("rows", { required: true })
const skipInvalid = defineModel<boolean>("skipInvalid", { required: true })
const props = defineProps<{ fileName: string; tiers: TierOption[] }>()
const emit = defineEmits<{ replace: [] }>()

const unknownTiers = computed(() => [
	...new Set(
		rows.value
			.map((row) => row.ticket_type)
			.filter((tier) => !props.tiers.some((option) => option.value === tier)),
	),
])
const broken = computed(() => {
	const duplicates = duplicateIds(rows.value)
	return rows.value
		.map((row, index) => ({
			row,
			index,
			problem: !isValidEmail(row.email)
				? "Invalid email"
				: duplicates.has(row.id)
					? "Already on the list"
					: null,
		}))
		.filter((entry) => entry.problem)
})
const openIssues = computed(
	() => unknownTiers.value.length + (broken.value.length && !skipInvalid.value ? 1 : 0),
)

const countFor = (tier: string) => rows.value.filter((row) => row.ticket_type === tier).length

function mapTier(from: string, to: string) {
	for (const row of rows.value) if (row.ticket_type === from) row.ticket_type = to
}
</script>

<template>
	<div class="space-y-4">
		<div class="flex items-center gap-2 text-p-sm text-ink-gray-6">
			<span class="lucide-file-spreadsheet size-4 text-ink-green-6" aria-hidden="true" />
			<span class="truncate font-medium text-ink-gray-9">{{ fileName }}</span>
			<span>· {{ rows.length }} rows</span>
			<Button variant="ghost" size="sm" label="Replace" @click="emit('replace')" />
		</div>

		<p class="text-lg font-semibold text-ink-gray-9">
			{{
				openIssues
					? `${openIssues} ${openIssues === 1 ? "thing" : "things"} to sort out`
					: "Everything checks out"
			}}
		</p>

		<div
			v-for="tier in unknownTiers"
			:key="tier"
			class="flex flex-wrap items-center gap-3 rounded-5 border border-outline-amber-2 bg-surface-amber-1 px-3 py-2.5"
		>
			<span class="lucide-tag size-4 shrink-0 text-ink-amber-6" aria-hidden="true" />
			<p class="min-w-0 flex-1 text-p-sm text-ink-gray-8">
				<span class="font-medium">“{{ tier }}”</span> isn't a tier on this event ·
				{{ guestCount(countFor(tier)) }}
			</p>
			<div class="w-44">
				<FormControl
					type="select"
					size="sm"
					placeholder="Use tier…"
					aria-label="Map to tier"
					:options="tiers"
					@update:model-value="mapTier(tier, $event)"
				/>
			</div>
		</div>

		<div
			v-if="broken.length"
			class="space-y-2 rounded-5 border px-3 py-2.5"
			:class="skipInvalid ? 'border-outline-gray-1' : 'border-outline-red-2 bg-surface-red-1'"
		>
			<div class="flex items-center gap-3">
				<span
					class="size-4 shrink-0"
					:class="
						skipInvalid ? 'lucide-check text-ink-gray-5' : 'lucide-circle-alert text-ink-red-6'
					"
					aria-hidden="true"
				/>
				<p class="min-w-0 flex-1 text-p-sm text-ink-gray-8">
					{{ broken.length }} {{ broken.length === 1 ? "row" : "rows" }} can't be invited
				</p>
				<Button
					size="sm"
					:variant="skipInvalid ? 'ghost' : 'outline'"
					:label="skipInvalid ? 'Undo' : 'Skip them'"
					@click="skipInvalid = !skipInvalid"
				/>
			</div>
			<ul class="space-y-1 pl-7 text-p-sm text-ink-gray-6">
				<li v-for="entry in broken" :key="entry.row.id">
					Row {{ entry.index + 2 }} · {{ entry.row.email }} — {{ entry.problem }}
				</li>
			</ul>
		</div>
	</div>
</template>
