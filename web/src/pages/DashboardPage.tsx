import {
  Badge,
  Box,
  Button,
  Card,
  Code,
  Flex,
  Heading,
  Separator,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from "@chakra-ui/react"
import * as React from "react"
import { LuArrowRight, LuCircleCheck, LuShieldCheck, LuTriangleAlert } from "react-icons/lu"

import { useAuth } from "@/auth/AuthProvider"
import { ApiError, api } from "@/lib/api"

export function DashboardPage() {
  const { user, token } = useAuth()
  const [message, setMessage] = React.useState<string | null>(null)
  const [pending, setPending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const displayName = user?.full_name?.trim() || user?.username || "there"

  async function callProtectedRoute() {
    if (!token) return
    setPending(true)
    setError(null)
    try {
      const response = await api.protectedMessage(token)
      setMessage(response.message)
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.detail : "Request failed unexpectedly.",
      )
    } finally {
      setPending(false)
    }
  }

  return (
    <Stack gap="10">
      <Stack gap="4">
        <Text textStyle="xs" color="fg.subtle" letterSpacing="0.14em" textTransform="uppercase">
          Overview
        </Text>
        <Heading as="h1" size="2xl" letterSpacing="-0.02em">
          Hello, {displayName}
        </Heading>
        <Text color="fg.muted" maxW="lg">
          Your session is authenticated with a bearer token issued by the Crolo API.
        </Text>
      </Stack>

      <SimpleGrid columns={{ base: 1, md: 2 }} gap="4">
        <Card.Root size="sm" bg="bg.panel" borderColor="border.muted">
          <Card.Header>
            <Flex align="center" justify="space-between" gap="3">
              <Card.Title fontSize="sm" fontWeight="medium" color="fg.muted">
                Account
              </Card.Title>
              <LuShieldCheck size={16} />
            </Flex>
          </Card.Header>
          <Card.Body>
            <Stack gap="3">
              <Row label="Username" value={user?.username ?? "—"} />
              <Separator borderColor="border.muted" />
              <Row label="Email" value={user?.email ?? "—"} />
              <Separator borderColor="border.muted" />
              <Row label="Full name" value={user?.full_name ?? "—"} />
            </Stack>
          </Card.Body>
        </Card.Root>

        <Card.Root size="sm" bg="bg.panel" borderColor="border.muted">
          <Card.Header>
            <Card.Title fontSize="sm" fontWeight="medium" color="fg.muted">
              Roles
            </Card.Title>
          </Card.Header>
          <Card.Body>
            <Stack gap="3">
              <Flex gap="2" flexWrap="wrap">
                {user && user.roles.length > 0 ? (
                  user.roles.map((role) => (
                    <Badge
                      key={role}
                      colorPalette="brand"
                      variant="subtle"
                      rounded="full"
                      px="2.5"
                      py="1"
                      textTransform="lowercase"
                    >
                      {role}
                    </Badge>
                  ))
                ) : (
                  <Text fontSize="sm" color="fg.subtle">
                    No roles assigned.
                  </Text>
                )}
              </Flex>
              <Text fontSize="xs" color="fg.subtle">
                Roles are managed by the backend.
              </Text>
            </Stack>
          </Card.Body>
        </Card.Root>
      </SimpleGrid>

      <Box
        bg="bg.panel"
        borderWidth="1px"
        borderColor="border.muted"
        rounded="lg"
        p={{ base: "5", md: "6" }}
      >
        <Stack gap="4">
          <Stack gap="1">
            <Text fontSize="sm" fontWeight="medium">
              Protected endpoint
            </Text>
            <Text fontSize="sm" color="fg.muted">
              Verify that the stored token still authorizes requests.
            </Text>
          </Stack>

          <Flex gap="3" flexWrap="wrap">
            <Button
              size="sm"
              variant="surface"
              colorPalette="gray"
              onClick={callProtectedRoute}
              loading={pending}
            >
              Call <Code size="sm">/protected</Code>
              <LuArrowRight />
            </Button>
          </Flex>

          {pending ? (
            <Skeleton height="10" rounded="md" />
          ) : message ? (
            <Flex
              align="center"
              gap="2.5"
              bg="bg.success"
              borderWidth="1px"
              borderColor="border.success"
              rounded="md"
              px="3.5"
              py="2.5"
            >
              <LuCircleCheck size={15} />
              <Text fontSize="sm" color="fg.success">
                {message}
              </Text>
            </Flex>
          ) : null}

          {error ? (
            <Flex
              align="center"
              gap="2.5"
              bg="bg.error"
              borderWidth="1px"
              borderColor="border.error"
              rounded="md"
              px="3.5"
              py="2.5"
            >
              <LuTriangleAlert size={15} />
              <Text fontSize="sm" color="fg.error">
                {error}
              </Text>
            </Flex>
          ) : null}
        </Stack>
      </Box>
    </Stack>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <Flex align="center" justify="space-between" gap="4">
      <Text fontSize="sm" color="fg.muted">
        {label}
      </Text>
      <Text fontSize="sm" fontWeight="medium" truncate>
        {value}
      </Text>
    </Flex>
  )
}
