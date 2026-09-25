<script setup lang="ts">
import { Button, PageHeader, PageHeaderMobile } from "frappe-ui"

import { useIsMobile } from "@/composables/useIsMobile"

// The page's own name, which on mobile moves up into the header.
defineProps<{ title: string }>()

const isMobile = useIsMobile()
</script>

<template>
	<PageHeaderMobile v-if="isMobile" :title="title">
		<template #suffix>
			<Button
				variant="ghost"
				icon="lucide-plus"
				label="Create Event"
				:route="{ name: 'create-event' }"
			/>
		</template>
	</PageHeaderMobile>

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
