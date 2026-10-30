<script setup lang="ts">
import { Button, ErrorMessage, Spinner } from "frappe-ui"
import { computed } from "vue"

import type { FrappeError } from "@/types"

import ScheduleToast from "../ScheduleToast.vue"
import { useBuilder } from "../useScheduleBoard"
import ScheduleMobileAddSheet from "./ScheduleMobileAddSheet.vue"
import ScheduleMobileAgenda from "./ScheduleMobileAgenda.vue"
import ScheduleMobileControls from "./ScheduleMobileControls.vue"
import ScheduleMobileEditSheet from "./ScheduleMobileEditSheet.vue"
import ScheduleMobileGrid from "./ScheduleMobileGrid.vue"
import ScheduleMobileHeader from "./ScheduleMobileHeader.vue"
import { provideScheduleMobile, useScheduleMobile } from "./useScheduleMobile"

defineProps<{ eventId: string }>()
const builder = useBuilder()
const mobile = useScheduleMobile()
provideScheduleMobile(mobile)

const loadError = computed(
	() => (builder.schedule.error ?? builder.opener.error) as FrappeError | null,
)
</script>

<template>
	<div class="fixed inset-0 z-10 flex flex-col bg-surface-base text-ink-gray-8">
		<ScheduleMobileHeader :event-id="eventId" />
		<div v-if="loadError" class="p-4"><ErrorMessage :message="loadError.message" /></div>
		<div v-else-if="!builder.draft.value" class="grid flex-1 place-items-center">
			<Spinner class="size-5" />
		</div>
		<template v-else>
			<ScheduleMobileControls />
			<ScheduleMobileAgenda v-if="mobile.view.value === 'list'" />
			<ScheduleMobileGrid v-else />
			<Button
				variant="solid"
				size="lg"
				icon-left="lucide-plus"
				label="Add session"
				class="fixed bottom-[max(1.25rem,env(safe-area-inset-bottom))] left-1/2 z-20 -translate-x-1/2 shadow-xl"
				@click="mobile.openAdd()"
			/>
		</template>
		<ScheduleToast
			v-if="!mobile.sheet.value"
			class="!bottom-[calc(5.5rem+env(safe-area-inset-bottom))]"
		/>
		<ScheduleMobileEditSheet />
		<ScheduleMobileAddSheet />
	</div>
</template>
