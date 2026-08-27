// Field groups for template options
const TEMPLATE_FIELD_GROUPS = {
	event_details: {
		label: __("Event Details"),
		fields: [
			"category",
			"host",
			"banner_image",
			"short_description",
			"about",
			"medium",
			"venue",
			"allow_guest_booking",
			"guest_verification_method",
			"time_zone",
		],
	},
	ticketing_settings: {
		label: __("Ticketing Settings"),
		fields: [
			"send_ticket_email",
			"apply_tax",
			"tax_label",
			"tax_percentage",
			"ticket_email_template",
			"ticket_print_format",
		],
	},
	sponsorship_settings: {
		label: __("Sponsorship Settings"),
		fields: [
			"auto_send_pitch_deck",
			"sponsor_deck_email_template",
			"sponsor_deck_reply_to",
			"sponsor_deck_cc",
			"sponsor_deck_attachments",
		],
	},
}

const MANDATORY_FIELDS = ["category", "host"]

const FIELD_LABELS = {
	category: __("Category"),
	host: __("Host"),
	banner_image: __("Banner Image"),
	short_description: __("Short Description"),
	about: __("About"),
	medium: __("Medium"),
	venue: __("Venue"),
	allow_guest_booking: __("Allow Guest Booking"),
	guest_verification_method: __("Guest Verification Method"),
	time_zone: __("Time Zone"),
	send_ticket_email: __("Send Ticket Email"),
	apply_tax: __("Tax Settings"),
	tax_label: __("Tax Label"),
	tax_percentage: __("Tax Percentage"),
	ticket_email_template: __("Ticket Email Template"),
	ticket_print_format: __("Ticket Print Format"),
	auto_send_pitch_deck: __("Auto Send Pitch Deck"),
	sponsor_deck_email_template: __("Sponsor Deck Email Template"),
	sponsor_deck_reply_to: __("Sponsor Deck Reply To"),
	sponsor_deck_cc: __("Sponsor Deck CC"),
	sponsor_deck_attachments: __("Sponsor Deck Attachments"),
	payment_gateways: __("Payment Gateways"),
	ticket_types: __("Ticket Types"),
	add_ons: __("Add-ons"),
	custom_fields: __("Custom Fields"),
}

function get_field_label(field) {
	return FIELD_LABELS[field] || field
}

function render_field_group(group_key, template) {
	let group = TEMPLATE_FIELD_GROUPS[group_key]
	let html = '<div class="template-section mt-3">'
	html += `<h6 class="text-muted">${group.label}</h6>`
	html += '<div class="row">'

	for (let field of group.fields) {
		let value = template[field]
		let has_value = value !== null && value !== undefined && value !== "" && value !== 0

		if (Array.isArray(value)) {
			has_value = value.length > 0
		}

		let label = get_field_label(field)

		html += `
			<div class="col-md-6 mb-2">
				<label class="d-flex align-items-center">
					<input type="checkbox" class="template-option mr-2" data-option="${field}" ${
						has_value ? "checked" : "disabled"
					}>
					${label}
					${!has_value ? '<span class="text-muted ml-1">(' + __("Not set") + ")</span>" : ""}
				</label>
			</div>
		`
	}

	html += "</div></div>"
	return html
}

function render_related_documents(template) {
	let html = '<div class="template-section mt-4">'
	html += `<h6 class="text-muted">${__("Related Documents")}</h6>`
	html += '<div class="row">'

	const related_items = [
		{ key: "payment_gateways", label: __("Payment Gateways"), data_key: "payment_gateways" },
		{
			key: "ticket_types",
			label: __("Ticket Types"),
			data_key: "template_ticket_types",
		},
		{ key: "add_ons", label: __("Add-ons"), data_key: "template_add_ons" },
		{
			key: "custom_fields",
			label: __("Custom Fields"),
			data_key: "template_custom_fields",
		},
	]

	for (let item of related_items) {
		let count = template[item.data_key] ? template[item.data_key].length : 0
		html += `
			<div class="col-md-6 mb-2">
				<label class="d-flex align-items-center">
					<input type="checkbox" class="template-option mr-2" data-option="${item.key}" ${
						count > 0 ? "checked" : ""
					} ${count === 0 ? "disabled" : ""}>
					${item.label} ${
						count > 0
							? `<span class="text-muted ml-1">(${count})</span>`
							: '<span class="text-muted ml-1">(' + __("None") + ")</span>"
					}
				</label>
			</div>
		`
	}

	html += "</div></div>"
	return html
}

function update_mandatory_fields_visibility(dialog, template) {
	let missing_fields = []

	for (let field of MANDATORY_FIELDS) {
		let template_has_value = template[field] && template[field] !== ""
		let checkbox = dialog
			.get_field("field_options")
			.$wrapper.find(`.template-option[data-option="${field}"]`)
		let is_checked = checkbox.is(":checked")

		if (!template_has_value || !is_checked) {
			missing_fields.push(field)
			dialog.get_field(field).df.hidden = 0
			dialog.get_field(field).df.reqd = 1
			dialog.get_field(field).refresh()
		} else {
			dialog.get_field(field).df.hidden = 1
			dialog.get_field(field).df.reqd = 0
			dialog.get_field(field).refresh()
		}
	}

	if (missing_fields.length > 0) {
		dialog.get_field("missing_fields_section").df.hidden = 0
		dialog.get_field("missing_fields_section").refresh()
		dialog
			.get_field("missing_fields_info")
			.$wrapper.html(
				`<p class="text-muted small">${__(
					"The following required fields are not set in the template or not selected. Please fill them in:",
				)}</p>`,
			)
	} else {
		dialog.get_field("missing_fields_section").df.hidden = 1
		dialog.get_field("missing_fields_section").refresh()
		dialog.get_field("missing_fields_info").$wrapper.html("")
	}
}

function bind_select_buttons(dialog) {
	dialog
		.get_field("select_buttons")
		.$wrapper.find(".select-all-btn")
		.on("click", function () {
			dialog
				.get_field("field_options")
				.$wrapper.find(".template-option:not(:disabled)")
				.prop("checked", true)
			update_mandatory_fields_visibility(dialog, dialog.template_data)
		})

	dialog
		.get_field("select_buttons")
		.$wrapper.find(".unselect-all-btn")
		.on("click", function () {
			dialog.get_field("field_options").$wrapper.find(".template-option").prop("checked", false)
			update_mandatory_fields_visibility(dialog, dialog.template_data)
		})
}

function render_template_options(dialog, template) {
	let buttons_html = `
		<div class="mb-3">
			<button class="btn btn-default btn-xs select-all-btn">${__("Select All")}</button>
			<button class="btn btn-default btn-xs unselect-all-btn">${__("Unselect All")}</button>
		</div>
	`
	dialog.get_field("select_buttons").$wrapper.html(buttons_html)

	let html = ""
	html += render_field_group("event_details", template)
	html += render_field_group("ticketing_settings", template)
	html += render_field_group("sponsorship_settings", template)
	html += render_related_documents(template)

	dialog.get_field("field_options").$wrapper.html(html)
	dialog.template_data = template

	update_mandatory_fields_visibility(dialog, template)
	bind_select_buttons(dialog)

	dialog.get_field("field_options").$wrapper.on("change", ".template-option", function () {
		update_mandatory_fields_visibility(dialog, dialog.template_data)
	})
}

function on_template_selected(dialog) {
	let template_name = dialog.get_value("template")
	if (!template_name) {
		dialog.get_field("field_options").$wrapper.html("")
		dialog.get_field("select_buttons").$wrapper.html("")
		return
	}

	frappe.call({
		method: "frappe.client.get",
		args: {
			doctype: "Event Template",
			name: template_name,
		},
		callback: function (r) {
			if (r.message) {
				render_template_options(dialog, r.message)
			}
		},
	})
}

function create_event_from_template(dialog, values) {
	let template_name = values.template
	let options = {}

	dialog
		.get_field("field_options")
		.$wrapper.find(".template-option:checked")
		.each(function () {
			options[$(this).data("option")] = 1
		})

	let additional_fields = {}
	for (let field of MANDATORY_FIELDS) {
		let field_obj = dialog.get_field(field)
		if (!field_obj.df.hidden && values[field]) {
			additional_fields[field] = values[field]
		}
	}

	frappe.call({
		method: "buzz.events.doctype.buzz_event.buzz_event.create_from_template",
		args: {
			template_name: template_name,
			options: JSON.stringify(options),
			additional_fields: JSON.stringify(additional_fields),
		},
		freeze: true,
		freeze_message: __("Creating Event..."),
		callback: function (r) {
			if (r.message) {
				dialog.hide()
				frappe.show_alert({
					message: __("Event created successfully"),
					indicator: "green",
				})
				frappe.set_route("Form", "Buzz Event", r.message)
			}
		},
	})
}

function show_create_from_template_dialog() {
	let dialog = new frappe.ui.Dialog({
		title: __("Create Event from Template"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "template",
				label: __("Select Template"),
				options: "Event Template",
				reqd: 1,
				change: function () {
					on_template_selected(dialog)
				},
			},
			{
				fieldtype: "Section Break",
				fieldname: "missing_fields_section",
				label: __("Required Fields"),
				depends_on: "eval:doc.template",
				hidden: 1,
			},
			{
				fieldtype: "HTML",
				fieldname: "missing_fields_info",
			},
			{
				fieldtype: "Link",
				fieldname: "category",
				label: __("Category"),
				options: "Event Category",
				hidden: 1,
			},
			{
				fieldtype: "Column Break",
			},
			{
				fieldtype: "Link",
				fieldname: "host",
				label: __("Host"),
				options: "Event Host",
				hidden: 1,
			},
			{
				fieldtype: "Section Break",
				fieldname: "options_section",
				label: __("Select What to Copy"),
				depends_on: "eval:doc.template",
			},
			{
				fieldtype: "HTML",
				fieldname: "select_buttons",
				depends_on: "eval:doc.template",
			},
			{
				fieldtype: "HTML",
				fieldname: "field_options",
				depends_on: "eval:doc.template",
			},
		],
		size: "large",
		primary_action_label: __("Create Event"),
		primary_action: function (values) {
			create_event_from_template(dialog, values)
		},
	})

	dialog.show()
}

frappe.listview_settings["Buzz Event"] = {
	onload: function (listview) {
		if (frappe.perm.has_perm("Event Template", 0, "read")) {
			listview.page.add_inner_button(__("Create from Template"), function () {
				show_create_from_template_dialog()
			})
		}
	},
}
