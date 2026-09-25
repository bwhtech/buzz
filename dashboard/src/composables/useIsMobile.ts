import { breakpointsTailwind, createSharedComposable, useBreakpoints } from "@vueuse/core"

export const useIsMobile = createSharedComposable(() =>
	useBreakpoints(breakpointsTailwind).smaller("md"),
)
