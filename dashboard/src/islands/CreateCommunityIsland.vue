<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

import SlugInput, { type Availability } from "@/components/common/SlugInput.vue"
import LoginDialog from "@/components/LoginDialog.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"
import { session } from "@/data/session"
import { selectTeam } from "@/data/teams"

type CreatedCommunity = { team: string; route: string }

const isOpen = defineModel<boolean>("open", { required: true })

// A guest's draft rides in the URL through login and signup; see keepDraftInUrl.
const draft = new URLSearchParams(window.location.search)
const teamName = ref(draft.get("name") || "")
const slug = ref(draft.get("slug") || "")
const slugEdited = ref(Boolean(draft.get("slug")))
const availability = ref<Availability | null>(null)

const urlPrefix = `${window.location.host}/community/`

const toSlug = (name: string) =>
	name
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+|-+$/g, "")

watch(teamName, (name) => slugEdited.value || (slug.value = toSlug(name)))

const checkSlug = useCall<Availability, { slug: string }>({
	url: "/api/v2/method/buzz.api.communities.check_community_slug",
	immediate: false,
})

const createCommunity = useCall<CreatedCommunity, { team_name: string; slug: string }>({
	url: "/api/v2/method/buzz.api.communities.create_community",
	method: "POST",
	immediate: false,
	onSuccess: () => window.history.replaceState(null, "", window.location.pathname),
})
const created = computed(() => createCommunity.data)
const liveUrl = computed(() => created.value && `${window.location.host}${created.value.route}`)

const canCreate = computed(() => Boolean(teamName.value.trim() && availability.value?.available))

// Login reloads the page and signup returns through the verification email to this URL,
// so the dialog reopens with what the person typed.
function keepDraftInUrl() {
	const params = new URLSearchParams({ create: "1", name: teamName.value, slug: slug.value })
	window.history.replaceState(null, "", `${window.location.pathname}?${params}`)
}

function create() {
	if (!session.isLoggedIn) {
		keepDraftInUrl()
		isOpen.value = false
		return useLoginDialog().open()
	}
	createCommunity.submit({ team_name: teamName.value.trim(), slug: slug.value })
}

// No router on a public page, so both destinations are full page loads.
const goTo = (url: string) => (window.location.href = url)

function openDashboard(team: string) {
	selectTeam(team)
	goTo(`/b/manage/communities/${team}/settings/display`)
}
</script>

<template>
	<Dialog
		v-model="isOpen"
		:title="created ? __('Your community is live') : __('Create a community')"
	>
		<p v-if="created" class="text-base text-ink-gray-6">
			{{ __("{0} is live at {1}.", [teamName, liveUrl]) }}
		</p>
		<form v-else class="flex flex-col gap-4" @submit.prevent="canCreate && create()">
			<FormControl
				v-model="teamName"
				:label="__('Community name')"
				:placeholder="__('Night Owls Bengaluru')"
				autocomplete="off"
				required
			/>
			<div class="flex flex-col gap-1.5">
				<span class="text-xs text-ink-gray-5">{{ __("Community URL") }}</span>
				<SlugInput
					v-model="slug"
					v-model:availability="availability"
					:prefix="urlPrefix"
					:label="__('Community URL')"
					:placeholder="__('night-owls')"
					:check="(value) => checkSlug.submit({ slug: value })"
					@update:model-value="slugEdited = true"
				/>
			</div>
			<ErrorMessage :message="createCommunity.error" />
		</form>

		<template #actions>
			<div v-if="created" class="flex gap-2">
				<Button variant="solid" :label="__('View page')" @click="goTo(created.route)" />
				<Button
					variant="outline"
					:label="__('Set up in dashboard')"
					@click="openDashboard(created.team)"
				/>
			</div>
			<Button
				v-else
				class="w-full"
				variant="solid"
				:label="session.isLoggedIn ? __('Create community') : __('Log in to create')"
				:disabled="!canCreate"
				:loading="createCommunity.loading"
				@click="create"
			/>
		</template>
	</Dialog>
	<LoginDialog />
</template>
