/**
 * Thin fetch wrapper around the Crolo FastAPI backend.
 *
 * The backend exposes an OAuth2 password flow (`POST /token`) plus
 * `/register/` and the protected `/users/me` endpoint.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api"

const TOKEN_STORAGE_KEY = "crolo.access_token"

export interface User {
  id: number | null
  username: string
  email: string | null
  full_name: string | null
  disabled: boolean | null
  roles: string[]
}

export interface DeckSummary {
  id: number
  title: string
  status: "draft" | "ready"
  total_items: number
  quiz_ready: number
  needs_review: number
  hidden: number
  source_filename: string
  package_version: number
  schema_version: number
  created_at: string | null
  updated_at: string | null
  last_played_at: string | null
  accuracy: number | null
  sessions_completed: number
}

export interface DeckItem {
  id: number
  position: number
  front: string
  reading: string
  meaning: string
  options: string[]
  correct_index: number
  needs_review: boolean
  hidden: boolean
}

export interface DeckDetail {
  deck: DeckSummary
  report: ImportReport
}

export interface ImportReport {
  total_notes: number
  parsed: number
  quiz_ready: number
  duplicates: number
  needs_review: number
  missing_meaning: number
  skipped: Record<string, number>
  skip_samples: Array<{ front: string; reason: string }>
  ambiguous: Array<{ front: string; readings: string[] }>
  plans: Record<
    string,
    {
      front: string | null
      reading: string | null
      meaning: string | null
      combined: string | null
      strategy: string
    }
  >
  items: number
  package_version: number
  collection_file: string
  schema_version: number
  media_count: number
  deck_name: string
  options: {
    four: number
    three: number
    two: number
    strategy_a: number
    strategy_b: number
  }
  warnings: string[]
}

export interface DeckItemPage {
  items: DeckItem[]
  total: number
  page: number
  page_size: number
}

export interface DeckItemUpdate {
  front?: string
  reading?: string
  meaning?: string
  options?: string[]
  correct_index?: number
  needs_review?: boolean
  hidden?: boolean
}

export interface SessionItem {
  id: number
  item_id: number | null
  position: number
  front: string
  options: string[]
  selected_index: number | null
  is_correct: boolean | null
  reading: string | null
  meaning: string | null
  correct_index: number | null
}

export interface SessionState {
  id: number
  deck_id: number
  deck_title: string
  mode: "instant" | "end"
  source: "all" | "unseen" | "weak"
  status: "active" | "finished"
  total: number
  answered: number
  correct: number
  items: SessionItem[]
}

export interface AnswerResult {
  item_id: number
  selected_index: number
  correct: boolean
  correct_index: number
  reading: string
  meaning: string
  answered: number
  correct_count: number
  total: number
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

/** Multipart upload cannot go through `request()` (it sets JSON headers). */
async function upload<T>(path: string, file: File, token: string): Promise<T> {
  const form = new FormData()
  form.append("file", file)

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
      body: form,
    })
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

  // --- decks ---------------------------------------------------------------

  async importDeck(file: File, token: string): Promise<DeckDetail> {
    return upload<DeckDetail>("/decks/import", file, token)
  },

  async listDecks(token: string): Promise<DeckSummary[]> {
    return request<DeckSummary[]>("/decks", {}, token)
  },

  async getDeck(deckId: number, token: string): Promise<DeckDetail> {
    return request<DeckDetail>(`/decks/${deckId}`, {}, token)
  },

  async renameDeck(deckId: number, title: string, token: string): Promise<DeckSummary> {
    return request<DeckSummary>(
      `/decks/${deckId}`,
      { method: "PATCH", body: JSON.stringify({ title }) },
      token,
    )
  },

  async deleteDeck(deckId: number, token: string): Promise<void> {
    await request<null>(`/decks/${deckId}`, { method: "DELETE" }, token)
  },

  async publishDeck(deckId: number, token: string): Promise<DeckSummary> {
    return request<DeckSummary>(`/decks/${deckId}/publish`, { method: "POST" }, token)
  },

  async listDeckItems(
    deckId: number,
    token: string,
    params: {
      page?: number
      pageSize?: number
      search?: string
      filter?: "all" | "ready" | "review" | "hidden" | "missing_meaning"
    } = {},
  ): Promise<DeckItemPage> {
    const query = new URLSearchParams()
    query.set("page", String(params.page ?? 1))
    query.set("page_size", String(params.pageSize ?? 50))
    if (params.search) query.set("search", params.search)
    if (params.filter && params.filter !== "all") query.set("filter", params.filter)
    return request<DeckItemPage>(`/decks/${deckId}/items?${query.toString()}`, {}, token)
  },

  async updateDeckItems(
    deckId: number,
    updates: Array<[number, DeckItemUpdate]>,
    token: string,
  ): Promise<DeckItemPage> {
    return request<DeckItemPage>(
      `/decks/${deckId}/items`,
      { method: "PATCH", body: JSON.stringify({ updates }) },
      token,
    )
  },

  async createDeckItem(
    deckId: number,
    payload: { front: string; reading: string; meaning?: string; options?: string[] },
    token: string,
  ): Promise<DeckItem> {
    return request<DeckItem>(
      `/decks/${deckId}/items`,
      { method: "POST", body: JSON.stringify(payload) },
      token,
    )
  },

  async deleteDeckItem(deckId: number, itemId: number, token: string): Promise<void> {
    await request<null>(`/decks/${deckId}/items/${itemId}`, { method: "DELETE" }, token)
  },

  async regenerateDeckItem(deckId: number, itemId: number, token: string): Promise<DeckItem> {
    return request<DeckItem>(
      `/decks/${deckId}/items/${itemId}/regenerate`,
      { method: "POST" },
      token,
    )
  },

  // --- quiz ----------------------------------------------------------------

  async startSession(
    deckId: number,
    payload: {
      mode: "instant" | "end"
      source: "all" | "unseen" | "weak"
      count?: number
      itemIds?: number[]
    },
    token: string,
  ): Promise<SessionState> {
    return request<SessionState>(
      `/decks/${deckId}/sessions`,
      {
        method: "POST",
        body: JSON.stringify({
          mode: payload.mode,
          source: payload.source,
          count: payload.count,
          item_ids: payload.itemIds,
        }),
      },
      token,
    )
  },

  async getSession(sessionId: number, token: string): Promise<SessionState> {
    return request<SessionState>(`/sessions/${sessionId}`, {}, token)
  },

  async answerSessionItem(
    sessionId: number,
    itemId: number,
    selectedIndex: number,
    token: string,
  ): Promise<AnswerResult> {
    return request<AnswerResult>(
      `/sessions/${sessionId}/answer`,
      { method: "POST", body: JSON.stringify({ item_id: itemId, selected_index: selectedIndex }) },
      token,
    )
  },

  async submitSessionAnswers(
    sessionId: number,
    answers: Array<{ item_id: number; selected_index: number }>,
    token: string,
  ): Promise<SessionState> {
    return request<SessionState>(
      `/sessions/${sessionId}/answers`,
      { method: "POST", body: JSON.stringify({ answers }) },
      token,
    )
  },

  async finishSession(sessionId: number, token: string): Promise<SessionState> {
    return request<SessionState>(`/sessions/${sessionId}/finish`, { method: "POST" }, token)
  },
}
