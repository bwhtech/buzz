import { breakpointsTailwind, createSharedComposable, useBreakpoints } from "@vueuse/core"

/** Below `md` the dashboard switches to frappe-ui's mobile shell, headers and sheets. */
export const useIsMobile = createSharedComposable(() =>
	useBreakpoints(breakpointsTailwind).smaller("md"),
)
