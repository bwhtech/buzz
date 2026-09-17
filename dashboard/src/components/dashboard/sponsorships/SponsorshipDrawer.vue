<script setup lang="ts">
import { Avatar, Button } from "frappe-ui"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"

export type DrawerDetail = { label: string; value?: string | null; link?: string | null }

withDefaults(
	defineProps<{
		title: string
		description: string
		image?: string | null
		details: DrawerDetail[]
		showAvatar?: boolean
		// Title sits beside the close button instead of heading the body.
		titleInHeader?: boolean
	}>(),
	{ image: null, showAvatar: true, titleInHeader: false },
)

const open = defineModel<boolean>("open", { required: true })
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<div class="flex items-center gap-1 p-4 pb-0">
				<DrawerClose as-child>
					<Button size="sm" icon="lucide-chevrons-right" aria-label="Close" />
				</DrawerClose>
				<template v-if="titleInHeader">
					<DrawerTitle class="ml-1 truncate text-lg font-semibold text-ink-gray-9">
						{{ title }}
					</DrawerTitle>
					<DrawerDescription class="sr-only">{{ description }}</DrawerDescription>
				</template>
				<div class="ml-auto flex items-center gap-1">
					<slot name="actions" />
				</div>
			</div>

			<div class="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
				<slot name="notice" />

				<div v-if="!titleInHeader" class="flex items-center gap-3">
					<Avatar
						v-if="showAvatar"
						:image="image || undefined"
						:label="title"
						size="2xl"
						shape="square"
					/>
					<div class="min-w-0 space-y-1">
						<DrawerTitle class="truncate text-xl font-semibold text-ink-gray-9">
							{{ title }}
						</DrawerTitle>
						<DrawerDescription class="truncate text-base text-ink-gray-5">
							{{ description }}
						</DrawerDescription>
					</div>
				</div>

				<slot name="badges" />

				<dl v-if="details.length" class="grid grid-cols-2 gap-x-5 gap-y-3">
					<div v-for="detail in details" :key="detail.label" class="min-w-0 space-y-0.5">
						<dt class="text-base text-ink-gray-5">{{ detail.label }}</dt>
						<dd class="truncate text-base text-ink-gray-8">
							<a
								v-if="detail.link && detail.value"
								:href="detail.link"
								target="_blank"
								rel="noopener"
								class="underline decoration-outline-gray-3 underline-offset-2 hover:text-ink-gray-9"
							>
								{{ detail.value }}
							</a>
							<span v-else-if="detail.value">{{ detail.value }}</span>
							<span v-else class="text-ink-gray-4">—</span>
						</dd>
					</div>
				</dl>

				<slot />
			</div>

			<template v-if="$slots.footer" #footer>
				<slot name="footer" />
			</template>
		</DrawerContent>
	</Drawer>
</template>
