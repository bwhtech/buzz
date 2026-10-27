import { useCall, useDoc } from "frappe-ui"
import { computed, ref } from "vue"

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

// What the builder edits; everything else on the doc is the server's to set.
const EDITABLE_FIELDS = ["title", "description", "questions"] as const

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))

export function useFormBuilder(formName: () => string) {
	const form = useDoc<BuzzFormDoc>({ doctype: "Buzz Form", name: formName })
	const draft = ref<BuzzFormDoc | null>(null)
	const savedSnapshot = ref("")

	function reset(doc: BuzzFormDoc) {
		draft.value = copy(doc)
		savedSnapshot.value = JSON.stringify(draft.value)
	}
	const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== savedSnapshot.value)
	// A refetch must not throw away edits the organiser has not saved.
	form.onSuccess((doc) => !dirty.value && reset(doc))

	async function save() {
		if (!draft.value) return
		const values = Object.fromEntries(EDITABLE_FIELDS.map((key) => [key, draft.value![key]]))
		reset((await form.setValue.submit(values)) as BuzzFormDoc)
	}

	const fieldsCall = useCall<{ fields: DoctypeField[] }, { form: string }>({
		url: "/api/v2/method/buzz.api.forms.get_form_builder_fields",
		params: () => ({ form: formName() }),
	})
	const doctypeFields = computed(() =>
		Object.fromEntries((fieldsCall.data?.fields ?? []).map((field) => [field.fieldname, field])),
	)

	return { form, draft, dirty, save, doctypeFields }
}

export type FormBuilder = ReturnType<typeof useFormBuilder>
