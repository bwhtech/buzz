<script setup lang="ts">
import { Alert } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"

// Each space of an event carries this itself, and the way back sits in the notice: the
// setting that undoes it lives on only one of them.
const props = defineProps<{ event: string }>()

const eventDoc = useEventDoc(() => props.event)

const archived = computed(() => Boolean(eventDoc.doc) && !eventDoc.doc?.is_published)
</script>

<template>
	<Alert v-if="archived" theme="amber" :title="__('This event is archived')">
		<template #description>
			{{ __("The event page is offline and its forms are no longer accepting responses.") }}
			<RouterLink
				:to="`/manage/events/${event}/more`"
				class="font-medium underline underline-offset-2"
			>
				{{ __("Unarchive the event") }}
			</RouterLink>
			{{ __("from More to bring it back online.") }}
		</template>
	</Alert>
</template>
