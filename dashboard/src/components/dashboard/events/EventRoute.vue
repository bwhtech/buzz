<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { computed, ref } from "vue"

import { checkEventRoute } from "@/data/events"

// The route the event already answers to, which is the one that opens and copies —
// an edit in the field is not a live address until it is saved.
const props = defineProps<{ event: string; saved: string | null }>()

const route = defineModel<string>({ default: "" })

// The host the dashboard is being used on, so the chip reads as the address it will be.
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
</script>

<template>
	<div class="w-80">
		<div class="flex items-center gap-1 rounded-4 bg-surface-gray-1 py-1 pl-2.5 pr-1 text-base">
			<span class="shrink-0 text-ink-gray-5">{{ hostname }}/</span>

			<input
				v-model="route"
				aria-label="Event route"
				placeholder="your-event"
				class="min-w-0 flex-1 bg-transparent text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none"
			/>

			<template v-if="saved">
				<a
					:href="publicPath"
					target="_blank"
					rel="noopener"
					aria-label="Open event page"
					class="shrink-0 rounded-4 p-1 text-ink-gray-5 transition-[color,transform] duration-150 ease-out hover:text-ink-gray-8 active:scale-95 motion-reduce:transition-none"
				>
					<span class="lucide-arrow-up-right block size-4" aria-hidden="true" />
				</a>

				<button
					type="button"
					aria-label="Copy"
					class="shrink-0 rounded-4 p-1 text-ink-gray-5 transition-[color,transform] duration-150 ease-out hover:text-ink-gray-8 active:scale-95 motion-reduce:transition-none"
					@click="copy"
				>
					<!-- Swapped, not crossfaded: at this size a fade reads as a flicker. -->
					<span
						class="block size-4"
						:class="justCopied ? 'lucide-check text-ink-gray-6' : 'lucide-copy'"
						aria-hidden="true"
					/>
				</button>
			</template>
		</div>

		<p
			v-if="availability"
			class="mt-1.5 flex items-center gap-1 text-sm"
			:class="availability.available ? 'text-ink-green-6' : 'text-ink-red-6'"
		>
			<span
				class="size-3.5 shrink-0"
				:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
				aria-hidden="true"
			/>
			{{ availability.message }}
		</p>
	</div>
</template>
