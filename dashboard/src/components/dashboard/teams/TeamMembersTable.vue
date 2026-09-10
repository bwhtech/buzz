<script setup lang="ts">
import { Avatar, Badge, Button, Checkbox, Dropdown, FormControl } from "frappe-ui"
import { computed, ref } from "vue"

import SelectionBar from "@/components/common/SelectionBar.vue"
import ChangeRoleDialog from "@/components/dashboard/teams/ChangeRoleDialog.vue"
import { useRosterActions } from "@/composables/useRosterActions"
import { useRowSelection } from "@/composables/useRowSelection"
import { session } from "@/data/session"
import type { TeamMember, TeamOverview } from "@/types"
import { canManageMembers } from "@/utils/teamRoles"
import { matchesQuery, rosterRows, type RosterRow } from "@/utils/teamRoster"

const props = defineProps<{ team: TeamOverview }>()
// One event for every action: the roster is reloaded either way.
const emit = defineEmits<{ changed: [] }>()

// Header and rows share one grid so the columns line up without a table element. Spelled
// out twice rather than composed: Tailwind only generates classes it can read in the source.
const COLUMNS = "grid grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_2rem] items-center gap-4"
const SELECTABLE_COLUMNS =
	"grid grid-cols-[1.25rem_minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_2rem] items-center gap-4"

const canManage = computed(() => canManageMembers(props.team.my_role))

// The checkbox column only exists for someone who can act on a selection.
const columns = computed(() => (canManage.value ? SELECTABLE_COLUMNS : COLUMNS))

const search = ref("")

const changing = ref<TeamMember[]>([])
const isChangingRole = ref(false)

const actions = useRosterActions(() => props.team.name, refreshed)

const rows = computed(() => rosterRows(props.team))

const visibleRows = computed(() => {
	const query = search.value.trim().toLowerCase()
	if (!query) return rows.value
	return rows.value.filter((row) => matchesQuery(row, query))
})

// Held against the whole roster, not the filtered view, so a search narrows what is on
// screen without quietly dropping what is already selected.
const selectableKeys = computed(() => rows.value.filter(isSelectable).map((row) => row.key))

const selection = useRowSelection(selectableKeys)

const selectedMembers = computed(() =>
	props.team.members.filter((member) => selection.isSelected(member.user)),
)

const visibleSelectableKeys = computed(() =>
	visibleRows.value.filter(isSelectable).map((row) => row.key),
)

const allVisibleSelected = computed(
	() =>
		visibleSelectableKeys.value.length > 0 &&
		visibleSelectableKeys.value.every(selection.isSelected),
)

// A row joins a selection only if both group actions apply to it, so an invitation —
// which is resent or retracted, never re-roled — stays on its own menu.
function isSelectable(row: RosterRow) {
	return Boolean(row.member && canAdminister(row.member))
}

// The owner is locked server-side, and changing your own standing on a team — leaving it,
// or demoting yourself out of managing it — is not something to do from the roster.
function canAdminister(member: TeamMember) {
	if (!canManage.value) return false
	return member.team_role !== "Owner" && member.user !== session.user
}

// Select-all covers what the search has left on screen; clearing covers everything.
function toggleAllVisible() {
	if (allVisibleSelected.value) selection.clear()
	else selection.select(visibleSelectableKeys.value)
}

// An invitation is resent or retracted; a member is re-roled or removed.
function actionsFor(row: RosterRow) {
	const member = row.member
	if (!member) return canManage.value ? inviteActions(row) : []
	if (!canAdminister(member)) return []
	return [
		{
			label: __("Change role"),
			icon: "lucide-refresh-ccw",
			onClick: () => openRoleChange([member]),
		},
		{
			label: __("Remove"),
			icon: "lucide-trash-2",
			theme: "red" as const,
			onClick: () => actions.confirmRemove([member]),
		},
	]
}

function inviteActions(row: RosterRow) {
	return [
		{
			label: __("Resend"),
			icon: "lucide-arrow-up-from-line",
			onClick: () => actions.resend(row),
		},
		{
			label: __("Retract"),
			icon: "lucide-shredder",
			theme: "red" as const,
			onClick: () => actions.confirmRetract(row),
		},
	]
}

function openRoleChange(members: TeamMember[]) {
	changing.value = members
	isChangingRole.value = true
}

// A selection is spent once it has been acted on, and the roster is reloaded under it.
function refreshed() {
	selection.clear()
	emit("changed")
}
</script>

<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-3">
			<FormControl
				v-model="search"
				type="text"
				class="max-w-xs"
				:placeholder="__('Search members')"
				:aria-label="__('Search members')"
			>
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</FormControl>

			<SelectionBar
				:count="selectedMembers.length"
				:label="__('{0} selected', [selectedMembers.length])"
				@clear="selection.clear()"
			>
				<Button
					icon-left="lucide-refresh-ccw"
					:label="__('Change role')"
					@click="openRoleChange(selectedMembers)"
				/>
				<Button
					theme="red"
					icon-left="lucide-trash-2"
					:label="__('Remove')"
					@click="actions.confirmRemove(selectedMembers)"
				/>
			</SelectionBar>
		</div>

		<div>
			<div :class="columns" class="pb-2 text-sm text-ink-gray-5">
				<Checkbox
					v-if="canManage"
					:model-value="allVisibleSelected"
					:indeterminate="!allVisibleSelected && selectedMembers.length > 0"
					:disabled="!visibleSelectableKeys.length"
					:aria-label="__('Select all members')"
					@update:model-value="toggleAllVisible"
				/>
				<span />
				<span />
				<span>{{ __("Role") }}</span>
			</div>

			<p v-if="!visibleRows.length" class="py-3 text-base text-ink-gray-5">
				{{ __("No members found") }}
			</p>

			<!-- Removing a row would otherwise snap the rest of the list upwards. -->
			<TransitionGroup tag="ul" name="member" :aria-label="__('Team members')" class="relative">
				<li
					v-for="row in visibleRows"
					:key="row.key"
					:class="columns"
					class="-mx-2 rounded-4 px-2 py-2 transition-colors duration-150 hover:bg-surface-gray-1"
				>
					<Checkbox
						v-if="canManage"
						:model-value="selection.isSelected(row.key)"
						:disabled="!isSelectable(row)"
						:aria-label="__('Select {0}', [row.name])"
						@update:model-value="selection.toggle(row.key)"
					/>

					<div class="flex min-w-0 items-center gap-3">
						<Avatar :image="row.image" :label="row.name" size="lg" />
						<span class="truncate text-base text-ink-gray-8">{{ row.name }}</span>
					</div>

					<!-- An invite has only an address, already shown as its name, so the cell
					     carries its pending state instead. -->
					<span class="flex min-w-0 items-center">
						<span v-if="row.member" class="truncate text-base text-ink-gray-6">{{
							row.email
						}}</span>
						<Badge v-else size="sm" variant="outline" :label="__('Invited')" />
					</span>

					<span class="truncate text-base font-medium text-ink-gray-8">{{ row.role }}</span>

					<Dropdown v-if="actionsFor(row).length" :options="actionsFor(row)" align="end">
						<!-- label is the accessible name here: an icon slot makes it icon-only. -->
						<Button
							variant="ghost"
							:label="row.member ? __('Member actions') : __('Invitation actions')"
						>
							<template #icon>
								<span class="lucide-ellipsis size-4" />
							</template>
						</Button>
					</Dropdown>
				</li>
			</TransitionGroup>
		</div>

		<ChangeRoleDialog
			v-model="isChangingRole"
			:team="team.name"
			:members="changing"
			@success="refreshed"
		/>
	</div>
</template>

<style scoped>
/* The leaving row is taken out of flow so the rows below start closing the gap
   straight away rather than waiting for the fade to finish. */
.member-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.member-leave-to {
	opacity: 0;
	transform: translateX(0.5rem);
}

.member-move {
	transition: transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.member-leave-to {
		transform: none;
	}

	.member-move {
		transition: none;
	}
}
</style>
