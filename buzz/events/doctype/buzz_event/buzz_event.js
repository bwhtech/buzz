// Copyright (c) 2025, BWH Studios and contributors
// For license information, please see license.txt

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
};

function get_field_label(field) {
	return FIELD_LABELS[field] || field;
}

function render_save_template_field_group(fields, doc) {
	let html = "";
	for (let field of fields) {
		let value = doc[field];
		let has_value = value !== null && value !== undefined && value !== "" && value !== 0;
		if (Array.isArray(value)) {
			has_value = value.length > 0;
		}
		let label = get_field_label(field);

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
		`;
	}
	return html;
}

function render_save_template_options(dialog, frm) {
	let html = "";
	let doc = frm.doc;

	let buttons_html = `
		<div class="mb-3">
			<button class="btn btn-default btn-xs select-all-btn">${__("Select All")}</button>
			<button class="btn btn-default btn-xs unselect-all-btn">${__("Unselect All")}</button>
		</div>
	`;
	dialog.get_field("select_buttons").$wrapper.html(buttons_html);

	// Event Details
	html += '<div class="template-section mt-3">';
	html += `<h6 class="text-muted">${__("Event Details")}</h6>`;
	html += '<div class="row">';
	html += render_save_template_field_group(
		[
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
		doc
	);
	html += "</div></div>";

	// Ticketing Settings
	html += '<div class="template-section mt-3">';
	html += `<h6 class="text-muted">${__("Ticketing Settings")}</h6>`;
	html += '<div class="row">';
	html += render_save_template_field_group(
		[
			"send_ticket_email",
			"apply_tax",
			"tax_label",
			"tax_percentage",
			"ticket_email_template",
			"ticket_print_format",
		],
		doc
	);
	html += "</div></div>";

	// Sponsorship Settings
	html += '<div class="template-section mt-3">';
	html += `<h6 class="text-muted">${__("Sponsorship Settings")}</h6>`;
	html += '<div class="row">';
	html += render_save_template_field_group(
		[
			"auto_send_pitch_deck",
			"sponsor_deck_email_template",
			"sponsor_deck_reply_to",
			"sponsor_deck_cc",
			"sponsor_deck_attachments",
		],
		doc
	);
	html += "</div></div>";

	// Related Documents
	html += '<div class="template-section mt-4" id="related-docs-section">';
	html += `<h6 class="text-muted">${__("Related Documents")}</h6>`;
	html += '<div class="row">';

	let pg_count = doc.payment_gateways ? doc.payment_gateways.length : 0;
	html += `
		<div class="col-md-6 mb-2">
			<label class="d-flex align-items-center">
				<input type="checkbox" class="template-option mr-2" data-option="payment_gateways" ${
					pg_count > 0 ? "checked" : ""
				} ${pg_count === 0 ? "disabled" : ""}>
				${__("Payment Gateways")} ${
		pg_count > 0
			? `<span class="text-muted ml-1">(${pg_count})</span>`
			: '<span class="text-muted ml-1">(' + __("None") + ")</span>"
	}
			</label>
		</div>
	`;

	html += `
		<div class="col-md-6 mb-2" id="ticket-types-option">
			<span class="text-muted">${__("Loading...")}</span>
		</div>
		<div class="col-md-6 mb-2" id="add-ons-option">
			<span class="text-muted">${__("Loading...")}</span>
		</div>
		<div class="col-md-6 mb-2" id="custom-fields-option">
			<span class="text-muted">${__("Loading...")}</span>
		</div>
	`;

	html += "</div></div>";

	dialog.get_field("field_options").$wrapper.html(html);

	let $wrapper = dialog.get_field("field_options").$wrapper;

	const linked_doctypes = [
		{
			id: "ticket-types-option",
			doctype: "Event Ticket Type",
			option: "ticket_types",
			label: __("Ticket Types"),
		},
		{
			id: "add-ons-option",
			doctype: "Ticket Add-on",
			option: "add_ons",
			label: __("Add-ons"),
		},
		{
			id: "custom-fields-option",
			doctype: "Buzz Custom Field",
			option: "custom_fields",
			label: __("Custom Fields"),
		},
	];

	for (let item of linked_doctypes) {
		frappe.call({
			method: "frappe.client.get_count",
			args: { doctype: item.doctype, filters: { event: doc.name } },
			callback: function (r) {
				let count = r.message || 0;
				$wrapper.find(`#${item.id}`).html(`
					<label class="d-flex align-items-center">
						<input type="checkbox" class="template-option mr-2" data-option="${item.option}" ${
					count > 0 ? "checked" : ""
				} ${count === 0 ? "disabled" : ""}>
						${item.label} ${
					count > 0
						? `<span class="text-muted ml-1">(${count})</span>`
						: '<span class="text-muted ml-1">(' + __("None") + ")</span>"
				}
					</label>
				`);
			},
		});
	}

	dialog
		.get_field("select_buttons")
		.$wrapper.find(".select-all-btn")
		.on("click", function () {
			dialog
				.get_field("field_options")
				.$wrapper.find(".template-option:not(:disabled)")
				.prop("checked", true);
		});

	dialog
		.get_field("select_buttons")
		.$wrapper.find(".unselect-all-btn")
		.on("click", function () {
			dialog
				.get_field("field_options")
				.$wrapper.find(".template-option")
				.prop("checked", false);
		});
}

function show_save_as_template_dialog(frm) {
	let dialog = new frappe.ui.Dialog({
		title: __("Save Event as Template"),
		fields: [
			{
				fieldtype: "Data",
				fieldname: "template_name",
				label: __("Template Name"),
				reqd: 1,
				default: frm.doc.title + " Template",
			},
			{
				fieldtype: "Section Break",
				label: __("Select What to Include"),
			},
			{
				fieldtype: "HTML",
				fieldname: "select_buttons",
			},
			{
				fieldtype: "HTML",
				fieldname: "field_options",
			},
		],
		size: "large",
		primary_action_label: __("Save Template"),
		primary_action: function (values) {
			let options = {};
			dialog
				.get_field("field_options")
				.$wrapper.find(".template-option:checked")
				.each(function () {
					options[$(this).data("option")] = 1;
				});

			frappe.call({
				method: "buzz.events.doctype.event_template.event_template.create_template_from_event",
				args: {
					event_name: frm.doc.name,
					template_name: values.template_name,
					options: JSON.stringify(options),
				},
				freeze: true,
				freeze_message: __("Creating Template..."),
				callback: function (r) {
					if (r.message) {
						dialog.hide();
						frappe.show_alert({
							message: __("Template {0} created successfully", [r.message]),
							indicator: "green",
						});
						frappe.set_route("Form", "Event Template", r.message);
					}
				},
			});
		},
	});

	render_save_template_options(dialog, frm);
	dialog.show();
}

frappe.ui.form.on("Buzz Event Form", {
	copy_to_clipboard(frm, cdt, cdn) {
		const row = frappe.get_doc(cdt, cdn);
		const url = `${window.location.origin}/b/${frm.doc.route}/${row.route}`;
		navigator.clipboard.writeText(url);
		frappe.show_alert({ message: __("Link copied!"), indicator: "green" });
	},
});

frappe.ui.form.on("Buzz Event", {
	refresh(frm) {
		frm.fields_dict.time_zone.set_data(getZoomSupportedTimezones());

		if (frm.doc.route && frm.doc.is_published) {
			frm.add_web_link(`/events/${frm.doc.route}`);
		}

		if (frm.doc.route) {
			frm.add_web_link(`/b/register/${frm.doc.route}`, "View Registration Page");
		}

		if (!frm.is_new()) {
			frm.add_web_link(`/b/check-in/${frm.doc.name}`, __("Open Check-in"));
		}

		const button_label = frm.doc.is_published ? __("Unpublish") : __("Publish");
		frm.add_custom_button(button_label, () => {
			frm.set_value("is_published", !frm.doc.is_published);
			frm.save();
		});

		frm.set_query("track", "schedule", (doc, cdt, cdn) => {
			return {
				filters: {
					event: doc.name,
				},
			};
		});

		frm.set_query("default_ticket_type", (doc) => {
			return {
				filters: {
					event: doc.name,
					is_published: 1,
				},
			};
		});

		// Save as Template button
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Save as Template"),
				function () {
					show_save_as_template_dialog(frm);
				},
				__("Actions")
			);
		}

		frm.trigger("add_zoom_custom_actions");
	},

	add_zoom_custom_actions(frm) {
		const installed_apps = frappe.boot.app_data.map((app) => app.app_name);
		if (!installed_apps.includes("zoom_integration") || frm.doc.category != "Webinars") {
			return;
		}

		if (frm.doc.zoom_webinar) {
			frm.add_custom_button(__("View Webinar on Zoom"), () => {
				window.open(`https://zoom.us/webinar/${frm.doc.zoom_webinar}`, "_blank");
			});
			return;
		}

		const btn = frm.add_custom_button(__("Create Webinar on Zoom"), () => {
			frm.call({
				doc: frm.doc,
				method: "create_webinar_on_zoom",
				btn,
				freeze: true,
			}).then(({ message }) => {
				frm.layout.tabs.find((t) => t.label == "Zoom Integration").set_active();
			});
		});
	},
	category(frm) {
		if (!frm.is_new()) return;

		if (frm.doc.category === "Webinars") {
			frm.set_value("attach_email_ticket", 0);
		} else {
			frm.set_value("attach_email_ticket", 1);
		}
	},
});

function getZoomSupportedTimezones() {
	return [
		"Pacific/Midway",
		"Pacific/Pago_Pago",
		"Pacific/Honolulu",
		"America/Anchorage",
		"America/Vancouver",
		"America/Los_Angeles",
		"America/Tijuana",
		"America/Edmonton",
		"America/Denver",
		"America/Phoenix",
		"America/Mazatlan",
		"America/Winnipeg",
		"America/Regina",
		"America/Chicago",
		"America/Mexico_City",
		"America/Guatemala",
		"America/El_Salvador",
		"America/Managua",
		"America/Costa_Rica",
		"America/Montreal",
		"America/New_York",
		"America/Indianapolis",
		"America/Panama",
		"America/Bogota",
		"America/Lima",
		"America/Halifax",
		"America/Puerto_Rico",
		"America/Caracas",
		"America/Santiago",
		"America/St_Johns",
		"America/Montevideo",
		"America/Araguaina",
		"America/Argentina/Buenos_Aires",
		"America/Godthab",
		"America/Sao_Paulo",
		"Atlantic/Azores",
		"Canada/Atlantic",
		"Atlantic/Cape_Verde",
		"UTC",
		"Etc/Greenwich",
		"Europe/Belgrade",
		"CET",
		"Atlantic/Reykjavik",
		"Europe/Dublin",
		"Europe/London",
		"Europe/Lisbon",
		"Africa/Casablanca",
		"Africa/Nouakchott",
		"Europe/Oslo",
		"Europe/Copenhagen",
		"Europe/Brussels",
		"Europe/Berlin",
		"Europe/Helsinki",
		"Europe/Amsterdam",
		"Europe/Rome",
		"Europe/Stockholm",
		"Europe/Vienna",
		"Europe/Luxembourg",
		"Europe/Paris",
		"Europe/Zurich",
		"Europe/Madrid",
		"Africa/Bangui",
		"Africa/Algiers",
		"Africa/Tunis",
		"Africa/Harare",
		"Africa/Nairobi",
		"Europe/Warsaw",
		"Europe/Prague",
		"Europe/Budapest",
		"Europe/Sofia",
		"Europe/Istanbul",
		"Europe/Athens",
		"Europe/Bucharest",
		"Asia/Nicosia",
		"Asia/Beirut",
		"Asia/Damascus",
		"Asia/Jerusalem",
		"Asia/Amman",
		"Africa/Tripoli",
		"Africa/Cairo",
		"Africa/Johannesburg",
		"Europe/Moscow",
		"Asia/Baghdad",
		"Asia/Kuwait",
		"Asia/Riyadh",
		"Asia/Bahrain",
		"Asia/Qatar",
		"Asia/Aden",
		"Asia/Tehran",
		"Africa/Khartoum",
		"Africa/Djibouti",
		"Africa/Mogadishu",
		"Asia/Dubai",
		"Asia/Muscat",
		"Asia/Baku",
		"Asia/Kabul",
		"Asia/Yekaterinburg",
		"Asia/Tashkent",
		"Asia/Calcutta",
		"Asia/Kathmandu",
		"Asia/Novosibirsk",
		"Asia/Almaty",
		"Asia/Dacca",
		"Asia/Krasnoyarsk",
		"Asia/Dhaka",
		"Asia/Bangkok",
		"Asia/Saigon",
		"Asia/Jakarta",
		"Asia/Irkutsk",
		"Asia/Shanghai",
		"Asia/Hong_Kong",
		"Asia/Taipei",
		"Asia/Kuala_Lumpur",
		"Asia/Singapore",
		"Australia/Perth",
		"Asia/Yakutsk",
		"Asia/Seoul",
		"Asia/Tokyo",
		"Australia/Darwin",
		"Australia/Adelaide",
		"Asia/Vladivostok",
		"Pacific/Port_Moresby",
		"Australia/Brisbane",
		"Australia/Sydney",
		"Australia/Hobart",
		"Asia/Magadan",
		"SST",
		"Pacific/Noumea",
		"Asia/Kamchatka",
		"Pacific/Fiji",
		"Pacific/Auckland",
		"Asia/Kolkata",
		"Europe/Kiev",
		"America/Tegucigalpa",
		"Pacific/Apia",
	];
}
