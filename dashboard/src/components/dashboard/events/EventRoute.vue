<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { computed, onBeforeUnmount, ref, watch } from "vue"

import { checkEventRoute } from "@/data/events"

// The route the event already answers to, which is the one that opens and copies —
// an edit in the field is not a live address until it is saved.
const props = defineProps<{ event: string; saved: string | null }>()

const route = defineModel<string>({ default: "" })
// Lifted so the page can refuse to save a slug the server has already claimed.
const taken = defineModel<boolean>("taken", { default: false })

// The host the dashboard is being used on, so the field reads as the address it will be.
const hostname = window.location.hostname
// Events are served under the dashboard's own base, not off the bare host.
const publicPath = computed(() => `/b/register/${props.saved}`)

type Availability = { available: boolean; message: string }
const availability = ref<Availability | null>(null)

// Only worth saying anything about a route that is not already this event's.
watchDebounced(
	route,
	async (value) => {
		availability.value = null
		if (!value.trim() || value === props.saved) return
		const answer = (await checkEventRoute.submit({
			route: value,
			event: props.event,
		})) as Availability
		// A later keystroke may have overtaken this request while it was in flight.
		if (route.value !== value) return
		availability.value = answer
	},
	{ debounce: 400 },
)

watch(availability, (answer) => (taken.value = Boolean(answer) && !answer?.available))

// The icon carries the confirmation, so this needs no toast on top of it.
const justCopied = ref(false)
let clearCopied: ReturnType<typeof setTimeout>

async function copy() {
	// The path the link opens, not the shorthand the chip reads.
	await navigator.clipboard.writeText(`${window.location.origin}${publicPath.value}`)
	justCopied.value = true
	clearTimeout(clearCopied)
	clearCopied = setTimeout(() => (justCopied.value = false), 1500)
}

onBeforeUnmount(() => clearTimeout(clearCopied))
</script>

<template>
	<div class="w-full space-y-1.5">
		<div class="flex items-center justify-between gap-2">
			<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">Event URL</h2>

			<div v-if="saved" class="flex items-center gap-1">
				<a
					:href="publicPath"
					target="_blank"
					rel="noopener"
					aria-label="Open event page"
					class="rounded-4 p-1 text-ink-gray-5 transition-[color,transform] duration-150 ease-out hover:text-ink-gray-8 active:scale-95 motion-reduce:transition-none"
				>
					<span class="lucide-arrow-up-right block size-4" aria-hidden="true" />
				</a>

				<button
					type="button"
					aria-label="Copy"
					class="rounded-4 p-1 text-ink-gray-5 transition-[color,transform] duration-150 ease-out hover:text-ink-gray-8 active:scale-95 motion-reduce:transition-none"
					@click="copy"
				>
					<!-- Swapped, not crossfaded: at this size a fade reads as a flicker. -->
					<span
						class="block size-4"
						:class="justCopied ? 'lucide-check text-ink-gray-6' : 'lucide-copy'"
						aria-hidden="true"
					/>
				</button>
			</div>
		</div>

		<!-- Host on its own line so a long slug keeps the full width to itself. The border
			 lights up on focus-within: the whole box is the field, not just the input. -->
		<div
			class="rounded-6 border border-outline-gray-2 px-2.5 py-1.5 transition-colors duration-150 ease-out focus-within:border-outline-gray-4 motion-reduce:transition-none"
		>
			<p class="text-xs leading-4 text-ink-gray-5">{{ hostname }}/</p>
			<input
				v-model="route"
				aria-label="Event route"
				placeholder="your-event"
				class="w-full bg-transparent text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none"
			/>
		</div>

		<!-- The answer lands 400ms after the last keystroke; without this it snaps in and
			 shoves the column. -->
		<Transition
			enter-active-class="transition duration-150 ease-out motion-reduce:transition-none"
			enter-from-class="opacity-0 -translate-y-0.5"
			leave-active-class="transition duration-100 ease-out motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<p
				v-if="availability"
				class="flex items-center gap-1 pt-0.5 text-sm"
				:class="availability.available ? 'text-ink-green-6' : 'text-ink-red-6'"
			>
				<span
					class="size-3.5 shrink-0"
					:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
					aria-hidden="true"
				/>
				{{ availability.message }}
			</p>
		</Transition>
	</div>
</template>
