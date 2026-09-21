<script setup lang="ts">
import { Badge, Breadcrumbs, Button, ErrorMessage, FormControl, PageHeader, toast } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import DuplicateThemeDialog from "@/components/dashboard/themes/DuplicateThemeDialog.vue"
import ThemePreview from "@/components/dashboard/themes/ThemePreview.vue"
import ThemeTokenField from "@/components/dashboard/themes/ThemeTokenField.vue"
import { useTheme, useThemeOptions } from "@/data/themes"
import type { ThemeDoc, ThemeToken } from "@/types"

const route = useRoute()
const theme = useTheme(() => route.params.themeName as string)
const options = useThemeOptions()

const draft = reactive<{ color_scheme: "dark" | "light"; tokens: ThemeToken[] }>({
	color_scheme: "dark",
	tokens: [],
})

const pickToken = ({ token, type, value, dark_value }: ThemeToken): ThemeToken => ({
	token,
	type,
	value,
	dark_value: dark_value ?? null,
})

function reset(doc: ThemeDoc) {
	draft.color_scheme = doc.color_scheme
	draft.tokens = doc.tokens.map(pickToken)
}

watch(
	() => theme.doc,
	(doc) => doc && reset(doc),
	{ immediate: true },
)

const savedDraft = computed(() =>
	theme.doc
		? JSON.stringify({
				color_scheme: theme.doc.color_scheme,
				tokens: theme.doc.tokens.map(pickToken),
			})
		: "",
)
const isDirty = computed(() => JSON.stringify(draft) !== savedDraft.value)

// Standard themes ship with the app and are replaced on update, so they are copied, not edited.
const readOnly = computed(() => Boolean(theme.doc?.is_standard) || !options.data?.can_edit)

const fontNames = computed(() => Object.keys(options.data?.fonts ?? {}))

const groups = computed(() =>
	[
		{ type: "Color", title: __("Colours") },
		{ type: "Font", title: __("Fonts") },
		{ type: "Dimension", title: __("Sizes") },
	].map((group) => ({ ...group, tokens: draft.tokens.filter((row) => row.type === group.type) })),
)

const duplicating = ref(false)

async function save() {
	await theme.setValue.submit({ ...draft }).catch(() => null)
	if (!theme.setValue.error) toast.success(__("Theme saved"))
}

async function toggleEnabled() {
	await theme.setValue.submit({ enabled: theme.doc?.enabled ? 0 : 1 }).catch(() => null)
}
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs
			:items="[
				{ label: __('Themes'), route: { name: 'themes' } },
				{ label: theme.doc?.name ?? '' },
			]"
		/>
		<div class="flex items-center gap-2">
			<Badge v-if="theme.doc?.is_standard" :label="__('Standard')" />
			<Button v-if="options.data?.can_edit" :label="__('Duplicate')" @click="duplicating = true" />
			<Button
				v-if="!readOnly"
				:label="theme.doc?.enabled ? __('Disable') : __('Enable')"
				:loading="theme.setValue.loading"
				@click="toggleEnabled"
			/>
			<Button
				v-if="!readOnly"
				variant="solid"
				:label="__('Save')"
				:disabled="!isDirty"
				:loading="theme.setValue.loading"
				@click="save"
			/>
		</div>
	</PageHeader>

	<div class="flex min-h-0 flex-1 gap-4 px-4 py-4">
		<aside class="w-80 shrink-0 space-y-6 overflow-y-auto pr-1">
			<ErrorMessage :message="theme.setValue.error" />
			<FormControl
				v-model="draft.color_scheme"
				type="select"
				:label="__('Default mode')"
				:options="[
					{ label: __('Dark'), value: 'dark' },
					{ label: __('Light'), value: 'light' },
				]"
				:disabled="readOnly"
			/>
			<section v-for="group in groups" :key="group.type" class="space-y-3">
				<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">
					{{ group.title }}
				</h2>
				<ThemeTokenField
					v-for="row in group.tokens"
					:key="row.token"
					v-model="row.value"
					v-model:dark-value="row.dark_value"
					:token="row"
					:fonts="fontNames"
					:disabled="readOnly"
				/>
			</section>
		</aside>

		<div class="min-h-[600px] flex-1">
			<ThemePreview
				v-if="options.data?.preview_route"
				:route="options.data.preview_route"
				:tokens="draft.tokens"
				:color-scheme="draft.color_scheme"
				:fonts="options.data.fonts"
			/>
			<EmptyState
				v-else-if="options.data"
				:title="__('Nothing to preview')"
				:description="__('Publish an event to preview themes on it.')"
			/>
		</div>
	</div>

	<DuplicateThemeDialog
		v-if="theme.doc"
		v-model="duplicating"
		:source="theme.doc.name"
		:color-scheme="draft.color_scheme"
		:tokens="draft.tokens"
	/>
</template>
