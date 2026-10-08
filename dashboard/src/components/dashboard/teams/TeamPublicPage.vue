<script setup lang="ts">
import { Button, ErrorMessage, Switch, Textarea, toast } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { computed, reactive, watch } from "vue"

import EventLinks from "@/components/dashboard/events/EventLinks.vue"
import { updatePublicPage } from "@/data/teams"
import type { EventExternalLink, TeamOverview } from "@/types"
import { richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"
import { serverErrorMessage } from "@/utils/serverError"
import { teamUrl } from "@/utils/teamUrl"

const props = defineProps<{ team: TeamOverview }>()
const emit = defineEmits<{ saved: [] }>()

function fromTeam(team: TeamOverview) {
	return {
		is_published: team.is_published,
		is_a_community: team.is_a_community,
		short_description: team.short_description ?? "",
		about: team.about ?? "",
		links: team.links.map((link) => ({ ...link })) as EventExternalLink[],
	}
}

const form = reactive(fromTeam(props.team))
let justSaved = false

function differsFrom(team: TeamOverview) {
	return JSON.stringify(form) !== JSON.stringify(fromTeam(team))
}

// The panel also reloads the team after a name or logo change; unsaved edits here survive that.
// The server refuses submissions on a private team, so unpublishing turns them off.
watch(
	() => form.is_published,
	(isPublic) => !isPublic && (form.is_a_community = false),
)

watch(
	() => props.team,
	(team, previous) => {
		if (justSaved || !differsFrom(previous)) Object.assign(form, fromTeam(team))
		justSaved = false
	},
)

const isDirty = computed(() => differsFrom(props.team))

async function save() {
	await updatePublicPage.submit({ team: props.team.name, ...form }).catch(() => null)
	if (updatePublicPage.error) return
	justSaved = true
	toast.success(__("Public page saved"))
	emit("saved")
}
</script>

<template>
	<section class="space-y-5">
		<div class="flex items-start justify-between gap-4">
			<div class="space-y-1">
				<h3 class="text-base-semibold text-ink-gray-8">{{ __("Public page") }}</h3>
				<a
					v-if="team.is_published && team.slug"
					:href="teamUrl(team.slug)"
					target="_blank"
					rel="noopener"
					class="text-p-sm text-ink-gray-5 underline-offset-2 hover:underline"
				>
					{{ teamUrl(team.slug) }}
				</a>
				<p v-else class="text-p-sm text-ink-gray-5">
					{{ __("Publish to give the team a page anyone can visit.") }}
				</p>
			</div>
			<Switch v-model="form.is_published" :label="__('Published')" />
		</div>

		<div v-if="form.is_published" class="flex items-start justify-between gap-4">
			<div class="space-y-1">
				<span class="text-base text-ink-gray-8">{{ __("Community") }}</span>
				<p class="text-p-sm text-ink-gray-5">
					{{ __("Other teams can submit events. Approved ones show on this page.") }}
				</p>
			</div>
			<Switch v-model="form.is_a_community" :aria-label="__('Community')" />
		</div>

		<Textarea
			v-model="form.short_description"
			:label="__('Short description')"
			:rows="2"
			:placeholder="__('One line about the team')"
		/>

		<div class="space-y-1.5">
			<span class="text-xs text-ink-gray-5">{{ __("About") }}</span>
			<div
				class="overflow-hidden rounded-6 border border-outline-gray-2 focus-within:border-outline-gray-4"
			>
				<Editor
					v-model="form.about"
					:extensions="richTextExtensions"
					:placeholder="__('What does the team do?')"
				>
					<EditorFixedMenu
						:items="richTextToolbar"
						class="overflow-x-auto border-b border-outline-gray-2 px-2 py-1"
					/>
					<EditorContent
						class="prose-sm h-40 max-w-none overflow-y-auto p-3 text-ink-gray-8 focus:outline-none"
					/>
				</Editor>
			</div>
		</div>

		<EventLinks
			v-model="form.links"
			class="rounded-6 border border-outline-gray-2 p-4"
			:hint="__('Website, forum, repository — wherever people can find the team.')"
		/>

		<ErrorMessage :message="serverErrorMessage(updatePublicPage.error)" />

		<div class="flex justify-end">
			<Button
				variant="solid"
				:label="__('Save')"
				:disabled="!isDirty"
				:loading="updatePublicPage.loading"
				@click="save"
			/>
		</div>
	</section>
</template>
