import { Button, Field, Input, InputGroup, Link, Spinner, Stack } from "@chakra-ui/react"
import * as React from "react"
import { LuMail, LuUser } from "react-icons/lu"
import { Link as RouterLink, useNavigate } from "react-router-dom"

import { AuthShell } from "@/components/AuthShell"
import { FormError } from "@/components/FormError"
import { PasswordInput } from "@/components/ui/password-input"
import { toaster } from "@/components/ui/toaster"
import { useAuth } from "@/auth/AuthProvider"
import { ApiError } from "@/lib/api"

const MIN_PASSWORD_LENGTH = 8

interface FormState {
  full_name: string
  username: string
  email: string
  password: string
}

const initialState: FormState = {
  full_name: "",
  username: "",
  email: "",
  password: "",
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = React.useState<FormState>(initialState)
  const [error, setError] = React.useState<string | null>(null)
  const [submitting, setSubmitting] = React.useState(false)

  const passwordTooShort =
    form.password.length > 0 && form.password.length < MIN_PASSWORD_LENGTH
  const canSubmit =
    form.full_name.trim() !== "" &&
    form.username.trim() !== "" &&
    form.email.trim() !== "" &&
    form.password.length >= MIN_PASSWORD_LENGTH

  function update(field: keyof FormState) {
    return (event: React.ChangeEvent<HTMLInputElement>) => {
      setForm((previous) => ({ ...previous, [field]: event.target.value }))
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    try {
      await register({
        full_name: form.full_name.trim(),
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
      })
      toaster.success({ title: "Account created", description: "You are signed in." })
      navigate("/", { replace: true })
    } catch (caught) {
      const message =
        caught instanceof ApiError
          ? caught.detail
          : "Something went wrong. Please try again."
      setError(message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthShell
      title="Create an account"
      subtitle="A single set of credentials for everything Crolo."
      footer={
        <>
          Already have an account?{" "}
          <Link asChild color="brand.fg" fontWeight="medium">
            <RouterLink to="/login">Sign in</RouterLink>
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Stack gap="5">
          {error ? <FormError>{error}</FormError> : null}

          <Field.Root>
            <Field.Label htmlFor="full_name">
              Full name
              <Field.RequiredIndicator />
            </Field.Label>
            <Input
              id="full_name"
              name="full_name"
              autoComplete="name"
              placeholder="Ada Lovelace"
              value={form.full_name}
              onChange={update("full_name")}
              required
            />
          </Field.Root>

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
                placeholder="ada"
                value={form.username}
                onChange={update("username")}
                required
              />
            </InputGroup>
          </Field.Root>

          <Field.Root>
            <Field.Label htmlFor="email">
              Email
              <Field.RequiredIndicator />
            </Field.Label>
            <InputGroup startElement={<LuMail />}>
              <Input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="ada@example.com"
                value={form.email}
                onChange={update("email")}
                required
              />
            </InputGroup>
          </Field.Root>

          <Field.Root invalid={passwordTooShort}>
            <Field.Label htmlFor="password">
              Password
              <Field.RequiredIndicator />
            </Field.Label>
            <PasswordInput
              id="password"
              name="password"
              autoComplete="new-password"
              placeholder="At least 8 characters"
              value={form.password}
              onChange={update("password")}
              required
            />
            {passwordTooShort ? (
              <Field.ErrorText>
                Use at least {MIN_PASSWORD_LENGTH} characters.
              </Field.ErrorText>
            ) : null}
          </Field.Root>

          <Button
            type="submit"
            colorPalette="brand"
            size="md"
            width="full"
            disabled={submitting || !canSubmit}
          >
            {submitting ? <Spinner size="sm" /> : "Create account"}
          </Button>
        </Stack>
      </form>
    </AuthShell>
  )
}
