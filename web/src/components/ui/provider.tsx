import { ChakraProvider } from "@chakra-ui/react"

import { system } from "@/theme"

/**
 * Crolo runs in a single, forced dark color mode, so no theme switcher or
 * `next-themes` integration is needed — `index.html` pins `class="dark"` and
 * the document `color-scheme`, and the system defaults resolve to dark values.
 */
export function Provider({ children }: { children: React.ReactNode }) {
  return <ChakraProvider value={system}>{children}</ChakraProvider>
}
