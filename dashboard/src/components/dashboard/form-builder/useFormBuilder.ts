import { useCall, useDoc } from "frappe-ui"
import { computed, ref } from "vue"

import type { LogicRule } from "@/utils/formLogic"

export interface FormQuestion {
	name?: string
	is_standard?: 0 | 1
	label: string
	fieldname: string
	fieldtype: string
	enabled: 0 | 1
	mandatory: 0 | 1
	options?: string | null
	placeholder?: string | null
	description?: string | null
	width?: "Full" | "Half"
	[key: string]: unknown
}

export interface BuzzFormDoc {
	name: string
	title: string
	description?: string | null
	event: string
	form_doctype: string
	route: string
	publish: 0 | 1
	questions: FormQuestion[]
	logic_rules: LogicRule[]
	login_required?: 0 | 1
	auto_close_at?: string | null
	submit_label?: string | null
	success_title?: string | null
	success_message?: string
	redirect_url?: string | null
	closed_title?: string | null
	closed_message?: string
	meta_title?: string | null
	meta_description?: string
	meta_image?: string | null
	og_image?: string | null
	[key: string]: unknown
}

// A field of the form's doctype, as the builder API describes it.
export interface DoctypeField {
	fieldname: string
	fieldtype: string
	label: string
	options: string | null
	link_options: { value: string; label: string }[] | null
	offered: boolean
	locked: boolean
}

// Where each form type lives in the event workspace, so the crumb leads back there.
export const FORM_SECTIONS: Record<string, { label: string; route: string }> = {
	"Talk Proposal": { label: "Talks", route: "event-talks" },
	"Sponsorship Enquiry": { label: "Sponsorships", route: "event-sponsorships" },
	"Event Booking": { label: "Registrations", route: "event-registrations" },
	"Event Booking Attendee": { label: "Registrations", route: "event-registrations" },
}

// What the builder edits; everything else on the doc is the server's to set.
const EDITABLE_FIELDS = [
	"title",
	"description",
	"questions",
	"logic_rules",
	"route",
	"publish",
	"login_required",
	"auto_close_at",
	"submit_label",
	"success_title",
	"success_message",
	"redirect_url",
	"closed_title",
	"closed_message",
	"meta_title",
	"meta_description",
	"meta_image",
] as const

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))

export function useFormBuilder(formName: () => string) {
	const form = useDoc<BuzzFormDoc>({ doctype: "Buzz Form", name: formName })
	const draft = ref<BuzzFormDoc | null>(null)
	const savedSnapshot = ref("")

	function reset(doc: BuzzFormDoc) {
		const rules = doc.logic_rules as unknown
		// JSON fields arrive as text; the builder edits the list.
		draft.value = {
			...copy(doc),
			logic_rules: typeof rules === "string" ? JSON.parse(rules) : (rules ?? []),
		}
		savedSnapshot.value = JSON.stringify(draft.value)
	}
	const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== savedSnapshot.value)
	// A refetch must not throw away edits the organiser has not saved.
	form.onSuccess((doc) => !dirty.value && reset(doc))

	async function save() {
		if (!draft.value) return
		const sent = JSON.stringify(draft.value)
		const values = Object.fromEntries(EDITABLE_FIELDS.map((key) => [key, draft.value![key]]))
		const saved = (await form.setValue.submit(values)) as BuzzFormDoc
		// Edits typed while the save was in flight stay in the draft for the next save.
		if (JSON.stringify(draft.value) === sent) adopt(saved)
		else savedSnapshot.value = sent
	}

	// Takes the saved form into the question objects already on screen, so a selection survives.
	function adopt(doc: BuzzFormDoc) {
		const shown = draft.value!.questions
		reset(doc)
		if (shown.length !== doc.questions.length) return
		draft.value!.questions = draft.value!.questions.map((question, index) =>
			Object.assign(shown[index], question),
		)
		savedSnapshot.value = JSON.stringify(draft.value)
	}

	const fieldsCall = useCall<
		{ fields: DoctypeField[]; attendee_form: string | null },
		{ form: string }
	>({
		url: "/api/v2/method/buzz.api.forms.get_form_builder_fields",
		params: () => ({ form: formName() }),
		// Held until there is a form to describe, then follows it.
		immediate: !!formName(),
		refetch: true,
	})
	const doctypeFields = computed(() =>
		Object.fromEntries((fieldsCall.data?.fields ?? []).map((field) => [field.fieldname, field])),
	)

	const attendeeForm = computed(() => fieldsCall.data?.attendee_form ?? "")

	return { form, draft, dirty, save, doctypeFields, attendeeForm }
}

export type FormBuilder = ReturnType<typeof useFormBuilder>
