import { Center, Spinner, Stack, Text } from "@chakra-ui/react"
import { Navigate, Outlet, useLocation } from "react-router-dom"

import { useAuth } from "@/auth/AuthProvider"

/** Blocks protected routes until the stored session has been validated. */
export function ProtectedRoute() {
  const { isAuthenticated, initializing } = useAuth()
  const location = useLocation()

  if (initializing) {
    return <SessionLoader label="Restoring your session" />
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return <Outlet />
}

/** Keeps signed-in users away from the login/register screens. */
export function GuestRoute() {
  const { isAuthenticated, initializing } = useAuth()

  if (initializing) {
    return <SessionLoader label="Checking your session" />
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}

function SessionLoader({ label }: { label: string }) {
  return (
    <Center minH="100dvh" bg="bg">
      <Stack align="center" gap="3">
        <Spinner size="md" color="brand.fg" />
        <Text fontSize="sm" color="fg.muted">
          {label}
        </Text>
      </Stack>
    </Center>
  )
}
