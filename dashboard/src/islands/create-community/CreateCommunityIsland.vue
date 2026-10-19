<script setup lang="ts">
import { Button, ErrorMessage, useCall, usePortalTarget } from "frappe-ui"
import { DialogContent, DialogPortal, DialogRoot, DialogTitle } from "reka-ui"
import { computed, ref, useTemplateRef } from "vue"

import SlugStatus from "@/components/common/SlugStatus.vue"
import LoginForm from "@/components/LoginForm.vue"
import { type Availability, useSlugAvailability } from "@/composables/useSlugAvailability"
import { session } from "@/data/session"

import QuestionStep from "./QuestionStep.vue"
import { openCreatedCommunity } from "./reveal"

type Step = "url" | "name" | "login"
type CreatedCommunity = { team: string; route: string }

const isOpen = defineModel<boolean>("open", { required: true })
const portalTarget = usePortalTarget()

// A guest's draft rides in the URL through login and signup; see keepDraftInUrl.
const draft = new URLSearchParams(window.location.search)
const slug = ref(draft.get("slug") || "")
const teamName = ref(draft.get("name") || "")
const step = ref<Step>(slug.value && teamName.value ? "name" : "url")

const urlPrefix = `${window.location.host}/community/`
const pageUrl = computed(() => urlPrefix + slug.value)

const checkSlug = useCall<Availability, { slug: string }>({
	url: "/api/v2/method/buzz.api.communities.check_community_slug",
	immediate: false,
})
const { availability, checking } = useSlugAvailability(slug, (value) =>
	checkSlug.submit({ slug: value }),
)

// Stays busy while the new page loads.
const opening = ref(false)
const createCommunity = useCall<CreatedCommunity, { team_name: string; slug: string }>({
	url: "/api/v2/method/buzz.api.communities.create_community",
	method: "POST",
	immediate: false,
	onSuccess: (created) => {
		opening.value = true
		openCreatedCommunity(teamName.value.trim(), created.route, stepRoot.value)
	},
})

const busy = computed(() => createCommunity.loading || opening.value)

const steps = computed<Step[]>(() =>
	session.isLoggedIn ? ["url", "name"] : ["url", "name", "login"],
)
const reached = (index: number) => index <= steps.value.indexOf(step.value)

// While typing: lowercase, a hyphen for anything else, no doubled hyphens.
const toSlug = (value: string) =>
	value
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, "-")
		.replace(/^-+/, "")
const titleize = (value: string) =>
	value
		.split("-")
		.filter(Boolean)
		.map((word) => word[0].toUpperCase() + word.slice(1))
		.join(" ")

function claimUrl() {
	slug.value = slug.value.replace(/-+$/, "")
	teamName.value ||= titleize(slug.value)
	step.value = "name"
}

function nameCommunity() {
	if (session.isLoggedIn)
		return createCommunity.submit({ team_name: teamName.value.trim(), slug: slug.value })
	keepDraftInUrl()
	step.value = "login"
}

// Login reloads the page and signup returns through the verification email to this URL,
// so the flow reopens on the name step with what the person typed.
function keepDraftInUrl() {
	const params = new URLSearchParams({ create: "1", name: teamName.value, slug: slug.value })
	window.history.replaceState(null, "", `${window.location.pathname}?${params}`)
}

const stepRoot = useTemplateRef<HTMLElement>("stepRoot")
function focusStep() {
	stepRoot.value?.querySelector<HTMLElement>("input, [data-autofocus]")?.focus()
}
</script>

<template>
	<DialogRoot v-model:open="isOpen">
		<DialogPortal :to="portalTarget">
			<DialogContent
				class="takeover fixed inset-0 z-50 flex flex-col bg-surface-elevation-1 text-ink-gray-9 outline-none"
				:aria-describedby="undefined"
				@open-auto-focus.prevent="focusStep"
				@escape-key-down="busy && $event.preventDefault()"
			>
				<header class="grid h-14 shrink-0 grid-cols-[1fr_auto_1fr] items-center px-4 sm:px-7">
					<DialogTitle class="truncate text-base font-medium text-ink-gray-7">
						{{ __("Create a community") }}
					</DialogTitle>
					<div class="flex gap-1" aria-hidden="true">
						<span
							v-for="(name, index) in steps"
							:key="name"
							class="h-[3px] w-6 rounded-full transition-colors duration-200"
							:class="reached(index) ? 'bg-surface-gray-7' : 'bg-surface-gray-3'"
						/>
					</div>
					<Button
						class="justify-self-end"
						variant="ghost"
						icon="lucide-x"
						:tooltip="__('Close')"
						:disabled="busy"
						@click="isOpen = false"
					/>
				</header>

				<main class="flex flex-1 justify-center overflow-y-auto px-5 pb-10 pt-12 sm:pt-24">
					<Transition
						enter-active-class="transition duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]"
						enter-from-class="opacity-0 translate-y-1.5 motion-reduce:translate-y-0"
						leave-active-class="transition-opacity duration-100 ease-[cubic-bezier(0.23,1,0.32,1)]"
						leave-to-class="opacity-0"
						mode="out-in"
						@after-enter="focusStep"
					>
						<div :key="step" ref="stepRoot" class="w-full max-w-[600px]">
							<QuestionStep
								v-if="step === 'url'"
								v-model="slug"
								:question="urlPrefix"
								:placeholder="__('your-community')"
								:cta="__('Continue')"
								:format="toSlug"
								:disabled="!availability?.available"
								@submit="claimUrl"
							>
								<template #status>
									<SlugStatus :checking="checking" :availability="availability">
										<span>{{ __("Lowercase letters, numbers and hyphens") }}</span>
									</SlugStatus>
								</template>
							</QuestionStep>

							<QuestionStep
								v-else-if="step === 'name'"
								v-model="teamName"
								:question="__('What should people call it?')"
								:placeholder="__('Night Owls Bengaluru')"
								:cta="session.isLoggedIn ? __('Create community') : __('Continue')"
								:disabled="!teamName.trim()"
								:loading="busy"
								@submit="nameCommunity"
							>
								<template #back>
									<Button
										class="-ms-2 self-start"
										variant="ghost"
										icon-left="lucide-arrow-left"
										:label="pageUrl"
										@click="step = 'url'"
									/>
								</template>
								<template #status>
									<ErrorMessage v-if="createCommunity.error" :message="createCommunity.error" />
									<span v-else>{{
										__("Shown at the top of your page. You can change it later.")
									}}</span>
								</template>
							</QuestionStep>

							<div v-else-if="step === 'login'" class="flex max-w-[400px] flex-col gap-6">
								<Button
									class="-ms-2 self-start"
									variant="ghost"
									icon-left="lucide-arrow-left"
									:label="__('Back')"
									@click="step = 'name'"
								/>
								<div class="flex flex-col gap-2">
									<h2
										class="text-[28px] font-semibold leading-tight tracking-[-0.03em] text-ink-gray-9 sm:text-[32px]"
									>
										{{ __("Last step. Sign in to publish") }}
									</h2>
									<p class="break-words text-base text-ink-gray-5">
										{{
											__("{0} goes live at {1} once you're in. Your draft is kept.", [
												teamName,
												pageUrl,
											])
										}}
									</p>
								</div>
								<LoginForm />
							</div>
						</div>
					</Transition>
				</main>
			</DialogContent>
		</DialogPortal>
	</DialogRoot>
</template>

<style scoped>
.takeover {
	--takeover-scale: 0.985;
}

.takeover[data-state="open"] {
	animation: takeover-in 240ms cubic-bezier(0.23, 1, 0.32, 1);
}

.takeover[data-state="closed"] {
	animation: takeover-out 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.takeover {
		--takeover-scale: 1;
	}
}

@keyframes takeover-in {
	from {
		opacity: 0;
		transform: scale(var(--takeover-scale));
	}
}

@keyframes takeover-out {
	to {
		opacity: 0;
		transform: scale(var(--takeover-scale));
	}
}
</style>
