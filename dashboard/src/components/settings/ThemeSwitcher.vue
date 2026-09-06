<script setup lang="ts">
import { type ColorScheme, useColorScheme } from "frappe-ui"
import { computed } from "vue"

import BuzzLogo from "@/components/common/BuzzLogo.vue"
import { userResource } from "@/data/user"

// One pane per window in the preview: `system` shows a light and a dark half side
// by side, the other two a single window. Follows Helpdesk's preferences switcher.
// The card clips its own corners, so a pane carries no radius of its own; only the
// miniature screen inside it does.
interface Pane {
	tone: "light" | "dark"
	containerClass: string
	screenClass: string
}

const { colorScheme, setColorScheme } = useColorScheme()

const brandImage = computed(() => userResource.data?.brand_image)

const themeOptions = computed<
	{ value: ColorScheme; label: string; panes: Pane[]; bars: boolean }[]
>(() => [
	{
		value: "light",
		label: __("Light"),
		bars: true,
		panes: [
			{
				tone: "light",
				containerClass: "pl-5 pt-3.5 bg-surface-gray-2",
				screenClass: "bg-white rounded-tl-3",
			},
		],
	},
	{
		value: "dark",
		label: __("Dark"),
		bars: true,
		panes: [
			{
				tone: "dark",
				containerClass: "pl-5 pt-3.5 bg-surface-gray-2",
				screenClass: "bg-gray-900 rounded-tl-3",
			},
		],
	},
	{
		value: "system",
		label: __("System"),
		bars: false,
		panes: [
			{
				tone: "light",
				containerClass: "flex flex-1 pl-5 pt-3.5 bg-surface-gray-2",
				screenClass: "bg-white rounded-tl-3 w-full",
			},
			{
				tone: "dark",
				containerClass: "flex flex-1 pl-5 pt-3.5 bg-surface-gray-3",
				screenClass: "bg-gray-900 rounded-tl-3 w-full",
			},
		],
	},
])
</script>

<template>
	<div class="flex items-center gap-3" role="radiogroup" :aria-label="__('Theme')">
		<button
			v-for="option in themeOptions"
			:key="option.value"
			type="button"
			role="radio"
			:aria-checked="colorScheme === option.value"
			:data-testid="`theme-option-${option.value}`"
			class="min-h-[42px] flex-1 overflow-hidden rounded-6 border text-left transition-colors duration-150 ease-out focus-visible:outline-none focus-visible:focus-ring"
			:class="colorScheme === option.value ? 'border-outline-gray-4' : 'border-outline-gray-1'"
			@click="setColorScheme(option.value)"
		>
			<div :class="{ flex: option.panes.length > 1 }">
				<div v-for="pane in option.panes" :key="pane.tone" :class="pane.containerClass">
					<div class="overflow-hidden" :class="pane.screenClass">
						<div
							class="flex gap-[3px] border-b px-1 py-[3px]"
							:class="pane.tone === 'light' ? 'border-gray-100' : 'border-gray-800'"
						>
							<div class="size-1.5 rounded-full bg-[#FF5F57]" />
							<div class="size-1.5 rounded-full bg-[#FEBC2D]" />
							<div class="size-1.5 rounded-full bg-[#28C840]" />
						</div>
						<div class="flex min-h-[41px] items-start justify-between gap-2 p-2.5 pb-1 pr-0">
							<div class="flex flex-1 items-center gap-1">
								<img v-if="brandImage" :src="brandImage" class="size-5 object-cover" alt="" />
								<BuzzLogo v-else class="size-5 shrink-0 text-ink-gray-5" />
							</div>
							<div v-if="option.bars" class="flex flex-1 flex-col gap-[5px]">
								<div
									v-for="bar in 3"
									:key="bar"
									class="h-1.5 w-full"
									:class="pane.tone === 'light' ? 'bg-gray-100' : 'bg-gray-800'"
								/>
							</div>
						</div>
					</div>
				</div>
			</div>
			<div class="flex items-center justify-between border-t px-3 py-2">
				<span class="text-base text-ink-gray-7">{{ option.label }}</span>
				<span
					class="size-3.5 rounded-full"
					:class="
						colorScheme === option.value
							? 'border-4 border-outline-gray-4'
							: 'border border-outline-gray-2'
					"
				/>
			</div>
		</button>
	</div>
</template>
