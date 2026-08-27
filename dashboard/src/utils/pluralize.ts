/**
 * Pluralize or singularize a word based on count
 * @param {number} count - The count to determine singular/plural
 * @param {string} singular - The singular form of the word
 * @param {string} plural - The plural form of the word (optional, defaults to singular + 's')
 * @returns {string} The correctly pluralized word with count
 */
export function pluralize(count: number, singular: string, plural?: string | null): string {
	// If no plural form is provided, default to singular + 's'
	const pluralForm = plural || `${singular}s`

	// Return singular for count of 1, plural for everything else (including 0)
	const word = count === 1 ? singular : pluralForm

	return `${count} ${word}`
}

/**
 * Get just the pluralized word without the count
 * @param {number} count - The count to determine singular/plural
 * @param {string} singular - The singular form of the word
 * @param {string} plural - The plural form of the word (optional, defaults to singular + 's')
 * @returns {string} The correctly pluralized word without count
 */
export function pluralizeWord(count: number, singular: string, plural?: string | null): string {
	const pluralForm = plural || `${singular}s`
	return count === 1 ? singular : pluralForm
}
