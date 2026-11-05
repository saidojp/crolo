/**
 * Thin fetch wrapper around the Crolo FastAPI backend.
 *
 * The backend exposes an OAuth2 password flow (`POST /token`) plus
 * `/register/` and the protected `/users/me` endpoint.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api"

const TOKEN_STORAGE_KEY = "crolo.access_token"

export interface User {
  username: string
  email: string | null
  full_name: string | null
  disabled: boolean | null
  roles: string[]
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterPayload {
  username: string
  email: string
  full_name: string
  password: string
}

/** Error thrown for any non-2xx response from the API. */
export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

export function getStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    } else {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
    }
  } catch {
    // Storage can be unavailable (private mode); auth simply won't persist.
  }
}

/** FastAPI returns `detail` either as a string or as a validation error array. */
function extractDetail(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === "string") {
      return detail
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            const msg = (item as { msg: unknown }).msg
            const loc = (item as { loc?: unknown }).loc
            const field = Array.isArray(loc) ? String(loc[loc.length - 1]) : null
            return field ? `${field}: ${String(msg)}` : String(msg)
          }
          return null
        })
        .filter((message): message is string => message !== null)
      if (messages.length > 0) {
        return messages.join(". ")
      }
    }
  }
  if (status === 401) {
    return "Invalid credentials"
  }
  return `Request failed with status ${status}`
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof URLSearchParams) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  headers.set("Accept", "application/json")
  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, "Cannot reach the API. Is the backend running?")
  }

  const isJson = response.headers
    .get("content-type")
    ?.includes("application/json")
  const body: unknown = isJson ? await response.json() : null

  if (!response.ok) {
    throw new ApiError(response.status, extractDetail(response.status, body))
  }

  return body as T
}

export const api = {
  /** OAuth2 password grant. The backend expects form-encoded input. */
  async login(username: string, password: string): Promise<TokenResponse> {
    const form = new URLSearchParams()
    form.set("username", username)
    form.set("password", password)
    return request<TokenResponse>("/token", { method: "POST", body: form })
  },

  async register(payload: RegisterPayload): Promise<User> {
    return request<User>("/register/", {
      method: "POST",
      body: JSON.stringify(payload),
    })
  },

  async me(token: string): Promise<User> {
    return request<User>("/users/me", {}, token)
  },

  async protectedMessage(token: string): Promise<{ message: string }> {
    return request<{ message: string }>("/protected", {}, token)
  },
}
