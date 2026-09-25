<script setup lang="ts">
import { Alert } from "frappe-ui"
import { computed } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"
import { useEventDoc } from "@/data/events"

// Each space of an event carries this itself, and the way back sits in the notice: the
// setting that undoes it lives on only one of them. On mobile the header renders it as a banner.
const props = defineProps<{ event: string; banner?: boolean }>()

const isMobile = useIsMobile()

const eventDoc = useEventDoc(() => props.event)

const archived = computed(() => Boolean(eventDoc.doc) && !eventDoc.doc?.is_published)

const visible = computed(() => archived.value && isMobile.value === props.banner)
</script>

<template>
	<Alert
		v-if="visible"
		theme="amber"
		:title="__('This event is archived')"
		class="dark:!bg-surface-gray-2"
		:class="{ 'rounded-none': banner }"
	>
		<template #description>
			{{ __("The event page is offline and its forms are no longer accepting responses.") }}
			<RouterLink
				:to="`/manage/events/${event}/more`"
				class="font-medium underline underline-offset-2"
			>
				{{ __("Unarchive the event") }}
			</RouterLink>
			{{ __("to make the event page live.") }}
		</template>
	</Alert>
</template>
