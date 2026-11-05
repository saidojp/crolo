import { Button, Field, Flex, Input, InputGroup, Link, Spinner, Stack, Text } from "@chakra-ui/react"
import * as React from "react"
import { LuLock, LuUser } from "react-icons/lu"
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom"

import { AuthShell } from "@/components/AuthShell"
import { FormError } from "@/components/FormError"
import { PasswordInput } from "@/components/ui/password-input"
import { toaster } from "@/components/ui/toaster"
import { useAuth } from "@/auth/AuthProvider"
import { ApiError } from "@/lib/api"

interface LocationState {
  from?: { pathname?: string }
}

export function LoginPage() {
  const { login, pending } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)

  const redirectTo =
    (location.state as LocationState | null)?.from?.pathname ?? "/"

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    try {
      await login(username.trim(), password)
      toaster.success({ title: "Welcome back" })
      navigate(redirectTo, { replace: true })
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.detail
          : "Something went wrong. Please try again."
      setError(message)
    }
  }

  return (
    <AuthShell
      title="Sign in"
      subtitle="Use your Crolo account to continue."
      footer={
        <>
          Don&apos;t have an account?{" "}
          <Link asChild color="brand.fg" fontWeight="medium">
            <RouterLink to="/register">Create one</RouterLink>
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Stack gap="5">
          {error ? <FormError>{error}</FormError> : null}

          <Field.Root>
            <Field.Label htmlFor="username">
              Username
              <Field.RequiredIndicator />
            </Field.Label>
            <InputGroup startElement={<LuUser />}>
              <Input
                id="username"
                name="username"
                autoComplete="username"
                placeholder="your-username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
              />
            </InputGroup>
          </Field.Root>

          <Field.Root>
            <Field.Label htmlFor="password">
              Password
              <Field.RequiredIndicator />
            </Field.Label>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </Field.Root>

          <Button
            type="submit"
            colorPalette="brand"
            size="md"
            width="full"
            disabled={pending || username.trim() === "" || password === ""}
          >
            {pending ? <Spinner size="sm" /> : "Sign in"}
          </Button>

          <Flex align="center" justify="center" gap="1.5" color="fg.subtle">
            <LuLock size={12} />
            <Text fontSize="xs">Tokens are stored locally and expire after 30 minutes.</Text>
          </Flex>
        </Stack>
      </form>
    </AuthShell>
  )
}
