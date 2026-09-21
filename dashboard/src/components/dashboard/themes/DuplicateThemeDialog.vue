<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { ref, watch } from "vue"
import { useRouter } from "vue-router"

import { useNewTheme } from "@/data/themes"
import type { ThemeToken } from "@/types"

const props = defineProps<{ source: string; colorScheme: "dark" | "light"; tokens: ThemeToken[] }>()
const isOpen = defineModel<boolean>({ required: true })

const router = useRouter()
const creator = useNewTheme()
const themeName = ref("")

watch(isOpen, (open) => {
	if (!open) return
	themeName.value = `${props.source} copy`
	creator.reset()
})

async function submit() {
	if (creator.loading || !themeName.value.trim()) return
	Object.assign(creator.doc, {
		theme_name: themeName.value.trim(),
		color_scheme: props.colorScheme,
		enabled: 1,
		tokens: props.tokens.map(({ token, type, value }) => ({ token, type, value })),
	})
	const theme = await creator.submit().catch(() => null)
	if (!theme) return
	toast.success(__("Theme created"))
	isOpen.value = false
	router.push({ name: "theme-editor", params: { themeName: theme.name } })
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Duplicate theme')">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl v-model="themeName" :label="__('Theme name')" autocomplete="off" required />
			<ErrorMessage :message="creator.error" />
		</form>
		<template #actions>
			<Button variant="solid" class="w-full" :loading="creator.loading" @click="submit">
				{{ __("Duplicate") }}
			</Button>
		</template>
	</Dialog>
</template>
