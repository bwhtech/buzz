<script setup lang="ts">
import { Divider, Radio, RadioGroup, TextInput } from "frappe-ui"

import ZoomLogo from "@/components/common/ZoomLogo.vue"

const choice = defineModel<"link" | "zoom">("choice", { required: true })
const link = defineModel<string>("link", { required: true })
</script>

<template>
	<div class="rounded-5 border border-outline-gray-2">
		<RadioGroup v-model="choice">
			<div class="p-3">
				<Radio value="link" description="Google Meet, Microsoft Teams, or any other link.">
					<template #label>
						<span class="flex items-center gap-2">
							<span class="lucide-link size-4 text-ink-gray-6" aria-hidden="true" />
							Add a meeting link
						</span>
					</template>
				</Radio>
				<!-- A collapsing grid row animates the height; `inert` keeps Tab out of the hidden input. -->
				<div
					class="grid transition-[grid-template-rows] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
					:class="
						choice === 'link' ? 'grid-rows-[1fr] duration-200' : 'grid-rows-[0fr] duration-150'
					"
					:inert="choice !== 'link'"
				>
					<div class="overflow-hidden">
						<div
							class="pb-0.5 pl-6 pr-0.5 pt-2 transition-[opacity,transform] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:translate-y-0"
							:class="
								choice === 'link'
									? 'opacity-100 duration-200'
									: '-translate-y-1 opacity-0 duration-150'
							"
						>
							<TextInput
								v-model="link"
								variant="outline"
								type="url"
								placeholder="https://…"
								aria-label="Meeting link"
							/>
						</div>
					</div>
				</div>
			</div>
			<Divider />
			<div class="p-3">
				<Radio value="zoom" description="Buzz books it and adds the join link to the event.">
					<template #label>
						<span class="flex items-center gap-2">
							<ZoomLogo class="size-4" />
							Create a Zoom meeting
						</span>
					</template>
				</Radio>
			</div>
		</RadioGroup>
	</div>
</template>
