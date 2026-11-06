/** Shared display helpers for deck and quiz screens. */

export const JP_FONT_STACK =
  '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", "Noto Sans JP", system-ui, sans-serif'

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  return `${Math.round(value * 100)}%`
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

export const SKIP_REASONS: Record<string, string> = {
  front_without_kanji: "Prompt has no kanji",
  empty_front: "Empty prompt",
  reading_not_found: "Reading not found",
  reading_invalid: "Reading is not hiragana",
  cloze_unsupported: "Cloze cards are not supported",
}
