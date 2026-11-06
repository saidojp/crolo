import { Box, type BoxProps, Text } from "@chakra-ui/react"
import type * as React from "react"

import { JP_FONT_STACK } from "@/lib/format"

/** A large Japanese prompt (kanji word) with the app's Japanese font stack. */
export function KanjiPrompt({
  children,
  size = "2xl",
  ...rest
}: { children: string; size?: "sm" | "md" | "lg" | "xl" | "2xl" } & BoxProps) {
  const sizes = {
    sm: "md",
    md: "2xl",
    lg: "4xl",
    xl: "5xl",
    "2xl": "7xl",
  } as const

  return (
    <Box
      fontFamily={JP_FONT_STACK}
      fontSize={sizes[size]}
      fontWeight="medium"
      letterSpacing="0.02em"
      lineHeight="1.15"
      {...rest}
    >
      {children}
    </Box>
  )
}

/** Hiragana rendering with a slightly looser rhythm than Latin text. */
export function Reading({
  children,
  ...rest
}: Omit<BoxProps, "children"> & { children: React.ReactNode }) {
  return (
    <Text fontFamily={JP_FONT_STACK} letterSpacing="0.04em" {...rest}>
      {children}
    </Text>
  )
}
