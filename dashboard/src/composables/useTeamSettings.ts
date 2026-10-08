import { toast } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import { reloadTeams, updatePublicPage, updateTeam, useTeamOverview } from "@/data/teams"
import type { EventExternalLink, TeamOverview } from "@/types"
import { canEditPublicPage, canManageMembers } from "@/utils/teamRoles"

function formFromTeam(team: TeamOverview) {
	return {
		team_name: team.team_name,
		slug: team.slug ?? "",
		logo: team.logo,
		short_description: team.short_description ?? "",
		// Not edited on Settings yet, but update_public_page takes the whole page.
		about: team.about ?? "",
		links: team.links.map((link) => ({ ...link })) as EventExternalLink[],
		is_published: team.is_published,
		accept_community_submissions: team.accept_community_submissions,
	}
}

// What update_public_page takes; the rest of the form is update_team's.
const PAGE_FIELDS = [
	"slug",
	"short_description",
	"about",
	"links",
	"is_published",
	"accept_community_submissions",
] as const

type SettingsForm = ReturnType<typeof formFromTeam>
const publicPageFields = (values: SettingsForm) =>
	Object.fromEntries(PAGE_FIELDS.map((field) => [field, values[field]]))

const EMPTY_TEAM = { team_name: "", logo: null, links: [] } as unknown as TeamOverview

/**
 * One form behind the Settings page's single Save. Name and logo go to update_team
 * (Owner/Admin); the rest goes to update_public_page (Owner/Admin/Manager).
 */
export function useTeamSettings(team: string) {
	const overview = useTeamOverview(team)
	const form = reactive(formFromTeam(EMPTY_TEAM))

	watch(
		() => overview.data,
		(data) => data && Object.assign(form, formFromTeam(data)),
		{ immediate: true },
	)

	// The server refuses submissions on a private team, so going private turns them off.
	watch(
		() => form.is_published,
		(isPublic) => !isPublic && (form.accept_community_submissions = false),
	)

	const canManage = computed(() => canManageMembers(overview.data?.my_role))
	const canEditPage = computed(() => canEditPublicPage(overview.data?.my_role))

	const savedForm = computed(() => formFromTeam(overview.data ?? EMPTY_TEAM))
	const identityDirty = computed(
		() => form.team_name !== savedForm.value.team_name || form.logo !== savedForm.value.logo,
	)
	const pageDirty = computed(
		() =>
			JSON.stringify(publicPageFields(form)) !== JSON.stringify(publicPageFields(savedForm.value)),
	)
	const isDirty = computed(() => Boolean(overview.data) && (identityDirty.value || pageDirty.value))
	// Set by the URL field once the server says another team has the slug.
	const slugTaken = ref(false)
	const canSave = computed(() => isDirty.value && !slugTaken.value)
	const saving = computed(() => updateTeam.loading || updatePublicPage.loading)
	// This save's own failure: the calls are shared, so one skipped this time still holds
	// the error from an earlier save.
	const error = ref<Error | null>(null)

	async function submitHasError(call: typeof updateTeam, params: Record<string, unknown>) {
		await call.submit(params).catch(() => null)
		error.value = call.error
		return Boolean(call.error)
	}

	async function save() {
		if (!canSave.value || saving.value) return
		if (!form.team_name.trim()) return toast.error(__("Team name is required"))
		error.value = null
		const identity = { team, team_name: form.team_name, logo: form.logo }
		if (identityDirty.value && (await submitHasError(updateTeam, identity))) return
		if (
			pageDirty.value &&
			(await submitHasError(updatePublicPage, { team, ...publicPageFields(form) }))
		)
			return
		await overview.reload()
		reloadTeams()
		toast.success(__("Settings saved"))
	}

	// A fresh copy: the saved snapshot must never share the links array with the form.
	const discard = () => Object.assign(form, formFromTeam(overview.data ?? EMPTY_TEAM))

	return reactive({
		overview,
		form,
		canManage,
		canEditPage,
		isDirty,
		slugTaken,
		saving,
		error,
		save,
		discard,
	})
}

export type TeamSettings = ReturnType<typeof useTeamSettings>
