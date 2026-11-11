<script setup lang="ts">
import { TabButtons } from "frappe-ui"

defineProps<{ enabled: boolean; offerHours: string; disabled: boolean }>()
const emit = defineEmits<{ toggle: [enabled: boolean]; hours: [hours: string] }>()

const HOURS = ["24", "48", "72"].map((value) => ({ label: `${value}h`, value }))
</script>

<template>
	<section class="space-y-3.5">
		<div class="space-y-1">
			<h2 class="text-lg font-semibold text-ink-gray-9">Waitlist</h2>
			<p class="text-base text-ink-gray-5">
				Let people queue up once a ticket type with a seat limit sells out
			</p>
		</div>
		<div
			class="rounded-6 border border-outline-gray-2 transition-[border-color] duration-150 ease-out hover:border-outline-gray-3 has-[input:focus-visible]:outline has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-outline-gray-5 motion-reduce:transition-none"
		>
			<label
				class="flex cursor-pointer items-center gap-3.5 p-3.5 has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60"
			>
				<span class="lucide-list-ordered size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
				<span class="flex flex-1 flex-col gap-0.5">
					<span class="text-base font-medium text-ink-gray-9">Waitlist for sold-out tickets</span>
					<span class="text-sm leading-snug text-ink-gray-5">
						{{ enabled ? "People can join the queue" : "Sold-out ticket types just show Sold out" }}
					</span>
				</span>
				<input
					type="checkbox"
					role="switch"
					class="sr-only"
					aria-label="Waitlist for sold-out tickets"
					:checked="enabled"
					:disabled="disabled"
					@change="emit('toggle', ($event.target as HTMLInputElement).checked)"
				/>
				<span
					class="relative h-5 w-9 shrink-0 rounded-full transition-colors duration-150 ease-out motion-reduce:transition-none"
					:class="enabled ? 'bg-surface-gray-9' : 'bg-surface-gray-4'"
					aria-hidden="true"
				>
					<span
						class="absolute left-0.5 top-0.5 size-4 rounded-full bg-surface-base shadow-sm transition-transform duration-150 ease-out motion-reduce:transition-none"
						:class="enabled && 'translate-x-4'"
					/>
				</span>
			</label>
			<Transition
				enter-active-class="transition duration-150 ease-out motion-reduce:transition-none"
				enter-from-class="opacity-0 -translate-y-1 motion-reduce:translate-y-0"
			>
				<div
					v-if="enabled"
					class="flex flex-wrap items-center gap-4 border-t border-outline-gray-2 px-3.5 py-3"
				>
					<div class="min-w-48 flex-1 space-y-0.5">
						<p class="text-base text-ink-gray-9">Payment link expires after</p>
						<p class="text-sm text-ink-gray-5">
							Unpaid approvals and invites lose their seat after this
						</p>
					</div>
					<TabButtons
						:model-value="offerHours"
						:options="HOURS"
						:disabled="disabled"
						@update:model-value="emit('hours', String($event))"
					/>
				</div>
			</Transition>
		</div>
	</section>
</template>
