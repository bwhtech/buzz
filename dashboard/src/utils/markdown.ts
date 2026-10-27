import DOMPurify from "dompurify"
import { marked } from "marked"

// Organisers write these messages, so a `javascript:` link must not reach the public page.
export const safeMarkdown = (text?: string | null) =>
	text ? DOMPurify.sanitize(marked(text) as string) : ""
