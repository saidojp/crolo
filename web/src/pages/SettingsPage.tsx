import { Button, Card, Heading, HStack, Separator, Stack, Text } from "@chakra-ui/react"
import { LuLogOut } from "react-icons/lu"
import { useNavigate } from "react-router-dom"

import { useAuth } from "@/auth/AuthProvider"

export function SettingsPage() {
  const { user, token, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <Stack gap="8" maxW="2xl">
      <Heading as="h1" size="xl" letterSpacing="-0.02em">
        Settings
      </Heading>

      <Card.Root size="sm" bg="bg.panel" borderColor="border.muted">
        <Card.Header>
          <Card.Title fontSize="sm" fontWeight="medium">
            Session
          </Card.Title>
          <Card.Description fontSize="sm" color="fg.muted">
            Details of the current access token.
          </Card.Description>
        </Card.Header>
        <Card.Body>
          <Stack gap="3">
            <HStack justify="space-between" gap="4">
              <Text fontSize="sm" color="fg.muted">
                Signed in as
              </Text>
              <Text fontSize="sm" fontWeight="medium">
                {user?.username ?? "—"}
              </Text>
            </HStack>
            <Separator borderColor="border.muted" />
            <HStack justify="space-between" gap="4">
              <Text fontSize="sm" color="fg.muted">
                Roles
              </Text>
              <Text fontSize="sm" fontWeight="medium">
                {user && user.roles.length > 0 ? user.roles.join(", ") : "—"}
              </Text>
            </HStack>
            <Separator borderColor="border.muted" />
            <HStack justify="space-between" gap="4" align="flex-start">
              <Text fontSize="sm" color="fg.muted" flexShrink="0">
                Token
              </Text>
              <Text
                fontSize="xs"
                fontFamily="mono"
                color="fg.muted"
                truncate
                title={token ?? ""}
              >
                {token ? `${token.slice(0, 24)}…` : "—"}
              </Text>
            </HStack>
          </Stack>
        </Card.Body>
        <Card.Footer>
          <Button variant="subtle" colorPalette="red" size="sm" onClick={handleLogout}>
            <LuLogOut />
            Sign out
          </Button>
        </Card.Footer>
      </Card.Root>
    </Stack>
  )
}
