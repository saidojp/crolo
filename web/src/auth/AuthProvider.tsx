import * as React from "react"

import {
  ApiError,
  api,
  getStoredToken,
  setStoredToken,
  type RegisterPayload,
  type User,
} from "@/lib/api"

interface AuthContextValue {
  user: User | null
  token: string | null
  /** True only while the stored session is validated on boot. */
  initializing: boolean
  /** True while a login/register request is in flight. */
  pending: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
}

const AuthContext = React.createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(() => getStoredToken())
  const [user, setUser] = React.useState<User | null>(null)
  const [initializing, setInitializing] = React.useState<boolean>(() =>
    Boolean(getStoredToken()),
  )
  const [pending, setPending] = React.useState(false)

  // Validate a persisted token once on boot and hydrate the current user.
  React.useEffect(() => {
    if (!token) {
      return
    }

    let cancelled = false

    api
      .me(token)
      .then((currentUser) => {
        if (!cancelled) {
          setUser(currentUser)
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        // An expired/invalid token must be dropped so the user can log in again.
        if (error instanceof ApiError && error.status === 401) {
          setStoredToken(null)
          setToken(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setInitializing(false)
        }
      })

    return () => {
      cancelled = true
    }
    // Re-validating is only needed when the token itself changes.
  }, [token])

  const login = React.useCallback(async (username: string, password: string) => {
    setPending(true)
    try {
      const { access_token } = await api.login(username, password)
      const currentUser = await api.me(access_token)
      setStoredToken(access_token)
      setToken(access_token)
      setUser(currentUser)
    } finally {
      setPending(false)
    }
  }, [])

  const register = React.useCallback(async (payload: RegisterPayload) => {
    await api.register(payload)
    // Registration does not issue a token, so sign in right after.
    const { access_token } = await api.login(payload.username, payload.password)
    const currentUser = await api.me(access_token)
    setStoredToken(access_token)
    setToken(access_token)
    setUser(currentUser)
  }, [])

  const logout = React.useCallback(() => {
    setStoredToken(null)
    setToken(null)
    setUser(null)
  }, [])

  const value = React.useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      initializing,
      pending,
      isAuthenticated: Boolean(token && user),
      login,
      register,
      logout,
    }),
    [user, token, initializing, pending, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = React.useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>")
  }
  return context
}
