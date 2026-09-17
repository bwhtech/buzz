<script setup lang="ts">
import { Button } from "frappe-ui"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"

// The title sits beside the close button; the body is the caller's to fill.
defineProps<{ title: string; description: string }>()

const open = defineModel<boolean>("open", { required: true })
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<div class="flex items-center gap-1 p-4 pb-0">
				<DrawerClose as-child>
					<Button size="sm" icon="lucide-chevrons-right" aria-label="Close" />
				</DrawerClose>
				<DrawerTitle class="ml-1 truncate text-lg font-semibold text-ink-gray-9">
					{{ title }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">{{ description }}</DrawerDescription>
				<div class="ml-auto flex items-center gap-1">
					<slot name="actions" />
				</div>
			</div>

			<div class="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
				<slot name="notice" />
				<slot />
			</div>

			<template v-if="$slots.footer" #footer>
				<slot name="footer" />
			</template>
		</DrawerContent>
	</Drawer>
</template>
