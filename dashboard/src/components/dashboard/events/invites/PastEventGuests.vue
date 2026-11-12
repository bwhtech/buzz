<script setup lang="ts">
import { Button, Checkbox, ErrorMessage, LoadingText } from "frappe-ui"
import { computed, ref } from "vue"

import { type Condition, ListFilters } from "@/components/common/filters"
import { useEventGuests } from "@/composables/useEventGuests"
import type { ListOrder } from "@/composables/useListQuery"
import type { EventGuest, FrappeError } from "@/types"

import type { Contact } from "./invites"

// Mounted per event (keyed by the parent), so the list loads only when its event is opened.
const props = defineProps<{
	event: string
	title: string
	isSelected: (email: string) => boolean
}>()
const emit = defineEmits<{ toggle: [contact: Contact]; selectAll: [contacts: Contact[]] }>()

const search = ref("")
const order = ref<ListOrder>("desc")
const conditions = ref<Condition[]>([])
const { guests, page, loadMore, loadingFirstPage, loadingMore } = useEventGuests(
	props.event,
	search,
	order,
	conditions,
)

function toContact(guest: EventGuest): Contact {
	const [first_name = "", ...rest] = (guest.attendee_name ?? "").split(" ")
	return {
		first_name,
		last_name: rest.join(" "),
		email: guest.attendee_email ?? "",
		note: guest.ticket_type ?? "",
	}
}

// One person can hold several tickets; they are one invitee.
const contacts = computed(() => {
	const byEmail = new Map(
		guests.value
			.filter((guest) => guest.attendee_email)
			.map((guest) => [guest.attendee_email, toContact(guest)]),
	)
	return [...byEmail.values()]
})
const allSelected = computed(
	() =>
		contacts.value.length > 0 && contacts.value.every((contact) => props.isSelected(contact.email)),
)
const fullName = (contact: Contact) =>
	[contact.first_name, contact.last_name].filter(Boolean).join(" ") || contact.email

function toggleAll() {
	if (!allSelected.value) return emit("selectAll", contacts.value)
	for (const contact of contacts.value) emit("toggle", contact)
}
</script>

<template>
	<div class="space-y-3">
		<div class="flex items-center justify-between gap-3">
			<div class="min-w-0">
				<h4 class="truncate text-base font-medium text-ink-gray-9">{{ title }}</h4>
				<p class="text-p-sm text-ink-gray-6">
					{{ page.data ? `${page.data.matched} of ${page.data.total} guests` : "Loading guests…" }}
				</p>
			</div>
			<Button
				size="sm"
				variant="ghost"
				:label="allSelected ? 'Deselect shown' : `Select ${contacts.length} shown`"
				:disabled="!contacts.length"
				@click="toggleAll"
			/>
		</div>

		<ListFilters
			v-model="conditions"
			v-model:search="search"
			v-model:order="order"
			:fields="page.data?.filter_fields ?? []"
			search-placeholder="Search by name or email"
		/>

		<ErrorMessage :message="(page.error as FrappeError | null)?.message" />
		<LoadingText v-if="loadingFirstPage" />
		<p v-else-if="!contacts.length" class="py-6 text-center text-p-sm text-ink-gray-5">
			No guests match.
		</p>

		<ul v-else class="-mx-2">
			<li v-for="contact in contacts" :key="contact.email">
				<label
					class="flex cursor-pointer items-center gap-3 rounded-4 px-2 py-2 transition-colors duration-100 hover:bg-surface-gray-2"
				>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-p-base text-ink-gray-9">{{ fullName(contact) }}</span>
						<span class="block truncate text-p-sm text-ink-gray-5">{{ contact.email }}</span>
					</span>
					<span
						class="hidden w-36 shrink-0 truncate text-right text-p-sm text-ink-gray-5 sm:block"
						>{{ contact.note }}</span
					>
					<Checkbox
						class="shrink-0"
						:model-value="isSelected(contact.email)"
						:aria-label="`Invite ${fullName(contact)}`"
						@update:model-value="emit('toggle', contact)"
					/>
				</label>
			</li>
		</ul>

		<Button
			v-if="page.data?.has_next_page"
			class="w-full"
			variant="ghost"
			label="Load more"
			:loading="loadingMore"
			@click="loadMore"
		/>
	</div>
</template>
