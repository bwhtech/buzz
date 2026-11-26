<script setup lang="ts">
import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"

// The title sits beside the close button; the body is the caller's to fill.
withDefaults(
	defineProps<{
		title: string
		description: string
		// Off for a drawer that creates something, so a stray click beside it loses nothing.
		closeOnOutsideClick?: boolean
	}>(),
	{ closeOnOutsideClick: true },
)

const open = defineModel<boolean>("open", { required: true })
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md" :close-on-outside-click="closeOnOutsideClick">
			<div class="flex items-center gap-1 p-4 pb-0">
				<DrawerCloseButton />
				<DrawerTitle class="ml-1 truncate text-lg font-semibold text-ink-gray-9">
					{{ title }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">{{ description }}</DrawerDescription>
				<div class="ml-auto flex items-center gap-1">
					<slot name="actions" />
				</div>
			</div>

			<div class="flex flex-1 flex-col gap-6 overflow-y-auto overscroll-contain p-4">
				<slot name="notice" />
				<slot />
			</div>

			<template v-if="$slots.footer" #footer>
				<slot name="footer" />
			</template>
		</DrawerContent>
	</Drawer>
</template>
