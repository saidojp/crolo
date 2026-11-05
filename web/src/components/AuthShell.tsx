import { Box, Flex, Stack, Text } from "@chakra-ui/react"

import { BrandMark } from "@/components/BrandMark"

interface AuthShellProps {
  title: string
  subtitle: string
  children: React.ReactNode
  footer?: React.ReactNode
}

/**
 * Centered, single-column layout shared by the sign-in and sign-up screens.
 * A soft accent glow keeps the dark canvas from reading as flat black.
 */
export function AuthShell({ title, subtitle, children, footer }: AuthShellProps) {
  return (
    <Flex
      minH="100dvh"
      align="center"
      justify="center"
      px="4"
      py="10"
      bg="bg"
      position="relative"
      overflow="hidden"
      _before={{
        content: '""',
        position: "absolute",
        top: "-30%",
        left: "50%",
        transform: "translateX(-50%)",
        width: "min(720px, 120vw)",
        height: "min(720px, 120vw)",
        borderRadius: "full",
        bg: "radial-gradient(circle, var(--chakra-colors-brand-700) 0%, transparent 62%)",
        opacity: 0.18,
        filter: "blur(40px)",
        pointerEvents: "none",
      }}
    >
      <Box w="full" maxW="sm" position="relative">
        <Stack gap="8">
          <Stack gap="6" align="flex-start">
            <BrandMark />
            <Stack gap="1.5">
              <Text
                as="h1"
                fontSize="xl"
                fontWeight="semibold"
                letterSpacing="-0.01em"
                color="fg"
              >
                {title}
              </Text>
              <Text fontSize="sm" color="fg.muted">
                {subtitle}
              </Text>
            </Stack>
          </Stack>

          <Box
            bg="bg.panel"
            rounded="xl"
            borderWidth="1px"
            borderColor="border.muted"
            p={{ base: "5", md: "6" }}
            boxShadow="0 1px 0 0 var(--chakra-colors-whiteAlpha-100) inset, 0 24px 48px -36px #000"
          >
            {children}
          </Box>

          {footer ? (
            <Text fontSize="sm" color="fg.muted" textAlign="center">
              {footer}
            </Text>
          ) : null}
        </Stack>
      </Box>
    </Flex>
  )
}
