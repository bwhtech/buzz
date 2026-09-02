import {
	Blockquote,
	Bold,
	BulletList,
	HeadingGroup,
	InsertLink,
	InsertTable,
	Italic,
	OrderedList,
	RichTextKit,
	Separator,
	Strike,
} from "frappe-ui/editor"

// No upload handler is wired for proposals, so the media extensions are off —
// otherwise the drop/paste paths would silently fail.
export const proposalEditorExtensions = [
	RichTextKit.configure({
		heading: { levels: [2, 3, 4, 5, 6] },
		image: false,
		imageGroup: false,
		imageViewer: false,
		video: false,
		attachment: false,
	}),
]

export const proposalEditorToolbar = [
	HeadingGroup,
	Separator,
	Bold,
	Italic,
	Strike,
	Separator,
	BulletList,
	OrderedList,
	Blockquote,
	InsertLink,
	InsertTable,
]
