<script setup lang="ts">
import { Badge, Breadcrumbs, Icon, PageHeader } from "frappe-ui"

import { useThemes } from "@/data/themes"

const themes = useThemes()
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs :items="[{ label: __('Themes') }]" />
	</PageHeader>

	<div class="m-auto w-full max-w-[800px] space-y-4 px-4 py-8">
		<p class="text-p-sm text-ink-gray-6">
			{{
				__(
					"Themes set the colours, fonts and sizes of public event pages. Duplicate a standard theme to make your own.",
				)
			}}
		</p>

		<div
			class="overflow-hidden rounded-6 border border-outline-gray-2 divide-y divide-outline-gray-1"
		>
			<RouterLink
				v-for="theme in themes.data"
				:key="theme.name"
				:to="{ name: 'theme-editor', params: { themeName: theme.name } }"
				class="flex items-center justify-between gap-3 p-4 transition-colors hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:focus-ring"
			>
				<span class="flex items-center gap-3">
					<Icon
						:name="theme.color_scheme === 'dark' ? 'lucide-moon' : 'lucide-sun'"
						class="size-4 text-ink-gray-5"
					/>
					<span class="font-medium text-base text-ink-gray-8">{{ theme.name }}</span>
				</span>
				<span class="flex items-center gap-2">
					<Badge v-if="theme.is_standard" :label="__('Standard')" />
					<Badge v-if="!theme.enabled" theme="amber" :label="__('Disabled')" />
				</span>
			</RouterLink>
		</div>
	</div>
</template>
