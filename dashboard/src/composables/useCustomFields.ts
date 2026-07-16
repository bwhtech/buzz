/**
 * Composable for handling custom field logic
 * Provides utilities for converting Frappe field types to form control types,
 * parsing field options, and generating placeholders.
 */

/**
 * Interface representing the structure of a Frappe Field
 */
export interface FrappeField {
	fieldname: string
	fieldtype: string
	label: string
	options?: string | any[]
	placeholder?: string
	mandatory?: number | boolean
	default_value?: string | number | boolean
	link_options?: SelectOption[]
}

export interface SelectOption {
	label: string
	value: string
}

/**
 * Convert Frappe field types to FormControl types
 * @param {string} fieldtype - Frappe field type
 * @returns {string} - FormControl type
 */
export function getFormControlType(
	fieldtype: string,
	options?: string,
): string {
	if (fieldtype === "Data" && options === "Email") return "email"
	if (fieldtype === "Data" && options === "URL") return "url"

	switch (fieldtype) {
		case "Phone":
			return "text"
		case "Email":
			return "email"
		case "Select":
			return "select"
		case "Number":
		case "Int":
		case "Float":
			return "number"
		case "Check":
			return "checkbox"
		case "Small Text":
			return "textarea"
		default:
			return "text"
	}
}

/**
 * Check if a field type requires a special date/time picker
 * @param {string} fieldtype - Frappe field type
 * @returns {boolean}
 */
export function isDateField(fieldtype: string): boolean {
	return fieldtype === "Date"
}

/**
 * Check if a field type requires a datetime picker
 * @param {string} fieldtype - Frappe field type
 * @returns {boolean}
 */
export function isDateTimeField(fieldtype: string): boolean {
	return fieldtype === "Datetime"
}

export function isTextareaField(fieldtype: string): boolean {
	return fieldtype === "Text Editor" || fieldtype === "Small Text"
}

/**
 * Get field options for select fields
 * @param {Object} field - Field definition object
 * @returns {Array} - Array of { label, value } objects
 */
export function getFieldOptions(field: FrappeField): SelectOption[] {
	const isSelectType =
		field.fieldtype === "Select" || field.fieldtype === "Multi Select"
	if (isSelectType && field.options) {
		let options = []

		if (typeof field.options === "string") {
			// Split by newlines, trim each option, and filter out empty ones
			// but preserve an empty first option as a placeholder
			const allOptions = field.options
				.split("\n")
				.map((option) => option.trim())
			const hasEmptyFirst = allOptions.length > 0 && allOptions[0].length === 0
			options = allOptions.filter((option) => option.length > 0)
			if (hasEmptyFirst) {
				options.unshift("")
			}
		} else if (Array.isArray(field.options)) {
			// If options is already an array
			options = field.options.filter((option) => {
				try {
					return option != null && String(option).trim().length > 0
				} catch {
					return false
				}
			})
		}

		const formattedOptions = options.map((option) => {
			const optionStr = String(option).trim()
			return {
				label: optionStr,
				value: optionStr,
			}
		})

		// Debug log for development
		if (
			process.env.NODE_ENV === "development" &&
			formattedOptions.length === 0 &&
			field.options
		) {
			console.warn(
				`CustomField "${field.fieldname}" has Select type but no valid options:`,
				field.options,
			)
		}

		return formattedOptions
	}
	return []
}

/**
 * Get placeholder text for a field
 * @param {Object} field - Field definition object
 * @returns {string} - Placeholder text
 */
export function getFieldPlaceholder(field: FrappeField): string {
	// If custom placeholder is provided, use it
	if (field.placeholder?.trim()) {
		const placeholder = field.placeholder.trim()
		return field.mandatory ? `${placeholder} (${__("required")})` : placeholder
	}

	// If no custom placeholder is provided, return empty string
	return ""
}

/**
 * Get the default value for a field
 * @param {Object} field - Field definition object
 * @param {Function} getFieldOptionsFn - Function to get field options
 * @returns {*} - Default value or empty string
 */
export function getFieldDefaultValue(
	field: FrappeField,
): string | number | boolean {
	// For checkbox fields, handle 0/1 values explicitly
	if (field.fieldtype === "Check") {
		if (field.default_value === 1 || field.default_value === "1") {
			return 1
		}
		return 0 // Default to unchecked
	}

	// Check for explicit default value (use != null to allow "0" and 0)
	if (field.default_value != null && field.default_value !== "") {
		return field.default_value
	}

	return ""
}
