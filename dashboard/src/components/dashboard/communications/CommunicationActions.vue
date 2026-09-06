<script setup lang="ts">
import { Button } from "frappe-ui"
import { ref } from "vue"

import EmailSettingsDialog from "@/components/dashboard/communications/EmailSettingsDialog.vue"
import { session } from "@/data/session"

defineProps<{ event: string; supportEmail: string | null; canEdit: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)

// Same press as QuickActionsRail, so the two rails answer a click the same way.
const PRESSABLE =
	"duration-150 ease-out active:scale-[0.98] !transition-[transform,background-color,color]"
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<section class="space-y-1">
		<Button
			:class="`w-full !justify-start ${PRESSABLE}`"
			variant="ghost"
			label="Email settings"
			@click="dialogOpen = true"
		>
			<template #prefix>
				<span class="lucide-mail size-4" aria-hidden="true" />
			</template>
		</Button>
		<!-- Where replies land is decided here, so the rail says it in full: the team's
		     address when there is one, otherwise the sender's own. -->
		<p class="break-all px-2 text-p-sm leading-5 text-ink-gray-5">
			<template v-if="supportEmail">
				Replies go to <span class="text-ink-gray-7">{{ supportEmail }}</span>
			</template>
			<template v-else>
				No support email set, so replies go to you at
				<span class="text-ink-gray-7">{{ session.user }}</span>
			</template>
		</p>
	</section>

	<EmailSettingsDialog
		v-model="dialogOpen"
		:event="event"
		:support-email="supportEmail"
		:can-edit="canEdit"
		@changed="emit('changed')"
	/>
</template>
