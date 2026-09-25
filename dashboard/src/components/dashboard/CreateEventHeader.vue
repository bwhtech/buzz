<script setup lang="ts">
import { Button, PageHeader, PageHeaderMobile } from "frappe-ui"

import UserMenu from "@/components/UserMenu.vue"
import { useIsMobile } from "@/composables/useIsMobile"

defineProps<{ title: string }>()

const isMobile = useIsMobile()
</script>

<template>
	<template v-if="isMobile">
		<PageHeaderMobile :title="title">
			<template #suffix>
				<UserMenu variant="sheet" />
			</template>
		</PageHeaderMobile>

		<Button
			class="fixed bottom-20 right-4 z-10 shadow-lg"
			variant="solid"
			size="lg"
			icon-left="lucide-plus"
			label="Create Event"
			:route="{ name: 'create-event' }"
		/>
	</template>

	<PageHeader v-else class="border-none pt-2 bg-surface-elevation-1">
		<Button
			class="ml-auto"
			variant="solid"
			icon-left="lucide-plus"
			label="Create Event"
			:route="{ name: 'create-event' }"
		/>
	</PageHeader>
</template>
