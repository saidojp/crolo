import { Box, Flex, Stack, Text } from "@chakra-ui/react"

/**
 * The Crolo wordmark. Kept deliberately quiet: a single accent square plus
 * letter-spaced lowercase type.
 */
export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  const square = size === "sm" ? "6" : "7"
  const fontSize = size === "sm" ? "sm" : "md"

  return (
    <Flex align="center" gap="2.5" userSelect="none">
      <Box
        boxSize={square}
        rounded="md"
        bgGradient="to-br"
        gradientFrom="brand.400"
        gradientTo="brand.700"
        boxShadow="0 0 0 1px var(--chakra-colors-brand-800), 0 0 18px -6px var(--chakra-colors-brand-500)"
        position="relative"
        _before={{
          content: '""',
          position: "absolute",
          inset: "30%",
          rounded: "sm",
          bg: "white/90",
          opacity: 0.9,
        }}
      />
      <Stack gap="0">
        <Text
          fontSize={fontSize}
          fontWeight="semibold"
          letterSpacing="0.18em"
          textTransform="lowercase"
          color="fg"
          lineHeight="1"
        >
          crolo
        </Text>
      </Stack>
    </Flex>
  )
}
