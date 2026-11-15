<script setup lang="ts">
import { Button, Dropdown, Tooltip, toast, useFileUpload } from "frappe-ui"
import { computed, useTemplateRef } from "vue"

import type { EmailAttachmentChoice } from "@/data/comments"

const props = defineProps<{ choices: EmailAttachmentChoice[] }>()

const attached = defineModel<EmailAttachmentChoice[]>({ required: true })

const picker = useTemplateRef<HTMLInputElement>("picker")
const uploader = useFileUpload()

const isAttached = (choice: EmailAttachmentChoice) =>
	attached.value.some((existing) => existing.key === choice.key)

const toggle = (choice: EmailAttachmentChoice) =>
	(attached.value = isAttached(choice)
		? attached.value.filter((existing) => existing.key !== choice.key)
		: [...attached.value, choice])

const options = computed(() => [
	...(props.choices.length
		? [
				{
					group: "From this booking",
					options: props.choices.map((choice) => ({
						label: choice.label,
						icon: isAttached(choice) ? "lucide-check" : choice.icon,
						onClick: () => toggle(choice),
					})),
				},
			]
		: []),
	{
		group: "Other",
		hideLabel: !props.choices.length,
		options: [
			{
				label: "Upload from computer",
				icon: "lucide-upload",
				onClick: () => picker.value?.click(),
			},
		],
	},
])

async function upload(event: Event) {
	const input = event.target as HTMLInputElement
	const files = Array.from(input.files ?? [])
	input.value = ""
	for (const file of files) {
		const uploaded = await uploader.upload(file, { private: true }).catch(() => null)
		const name = uploaded?.name
		if (!name) {
			toast.error(`Could not upload ${file.name}`)
			continue
		}
		attached.value = [
			...attached.value,
			{
				key: name,
				label: file.name,
				fileName: file.name,
				icon: "lucide-paperclip",
				source: { kind: "file", file: name },
			},
		]
	}
}
</script>

<template>
	<Dropdown :options="options" side="top" align="start">
		<Tooltip text="Attach files">
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-paperclip"
				aria-label="Attach files"
				:loading="uploader.isUploading.value"
			/>
		</Tooltip>
	</Dropdown>
	<input ref="picker" type="file" multiple class="hidden" @change="upload" />
</template>
