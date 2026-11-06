import {
  Badge,
  Box,
  Button,
  Card,
  Center,
  Checkbox,
  Collapsible,
  Flex,
  Heading,
  IconButton,
  Input,
  Skeleton,
  Spinner,
  Stack,
  Table,
  Text,
  Textarea,
} from "@chakra-ui/react"
import * as React from "react"
import {
  LuArrowLeft,
  LuChevronDown,
  LuChevronRight,
  LuCirclePlus,
  LuEyeOff,
  LuEye,
  LuPlay,
  LuRefreshCw,
  LuSave,
  LuSearch,
  LuTrash2,
} from "react-icons/lu"
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom"

import { AddQuestionDialog } from "@/components/AddQuestionDialog"
import { DeckReport } from "@/components/DeckReport"
import { toaster } from "@/components/ui/toaster"
import { useAuth } from "@/auth/AuthProvider"
import {
  ApiError,
  type DeckDetail,
  type DeckItem,
  type DeckItemUpdate,
  type ImportReport,
  api,
} from "@/lib/api"
import { formatPercent, pluralize } from "@/lib/format"

type Filter = "all" | "ready" | "review" | "hidden" | "missing_meaning"

const FILTERS: Array<{ value: Filter; label: string }> = [
  { value: "all", label: "All" },
  { value: "ready", label: "Ready" },
  { value: "review", label: "Needs review" },
  { value: "hidden", label: "Hidden" },
  { value: "missing_meaning", label: "No translation" },
]

const PAGE_SIZE = 25

export function DeckDetailPage() {
  const { deckId: deckIdParam } = useParams()
  const deckId = Number(deckIdParam)
  const navigate = useNavigate()
  const { token } = useAuth()

  const [detail, setDetail] = React.useState<DeckDetail | null>(null)
  const [items, setItems] = React.useState<DeckItem[]>([])
  const [total, setTotal] = React.useState(0)
  const [page, setPage] = React.useState(1)
  const [filter, setFilter] = React.useState<Filter>("all")
  const [search, setSearch] = React.useState("")
  const [loading, setLoading] = React.useState(true)
  const [saving, setSaving] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [drafts, setDrafts] = React.useState<Record<number, DeckItemUpdate>>({})
  const [showReport, setShowReport] = React.useState(false)
  const [addOpen, setAddOpen] = React.useState(false)

  const dirtyCount = Object.keys(drafts).length

  const loadDeck = React.useCallback(async () => {
    if (!token || !Number.isFinite(deckId)) return
    const response = await api.getDeck(deckId, token)
    setDetail(response)
    return response
  }, [deckId, token])

  const loadItems = React.useCallback(async () => {
    if (!token || !Number.isFinite(deckId)) return
    const response = await api.listDeckItems(deckId, token, {
      page,
      pageSize: PAGE_SIZE,
      search,
      filter,
    })
    setItems(response.items)
    setTotal(response.total)
  }, [deckId, token, page, search, filter])

  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([loadDeck(), loadItems()])
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.detail : "Could not load the deck")
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [loadDeck, loadItems])

  // Reset to page 1 whenever the filter changes.
  React.useEffect(() => {
    setPage(1)
  }, [filter])

  function applyDraft(itemId: number, patch: DeckItemUpdate) {
    setDrafts((current) => {
      const merged = { ...current[itemId], ...patch }
      const next = { ...current, [itemId]: merged }
      return next
    })
  }

  async function saveChanges() {
    if (!token || dirtyCount === 0) return
    setSaving(true)
    try {
      const updates = Object.entries(drafts).map(
        ([id, update]) => [Number(id), update] as [number, DeckItemUpdate],
      )
      await api.updateDeckItems(deckId, updates, token)
      setDrafts({})
      toaster.success({
        title: "Changes saved",
        description: pluralize(updates.length, "question") + " updated",
      })
      await Promise.all([loadDeck(), loadItems()])
    } catch (caught) {
      toaster.error({
        title: "Could not save",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    } finally {
      setSaving(false)
    }
  }

  async function regenerate(item: DeckItem) {
    if (!token) return
    try {
      const updated = await api.regenerateDeckItem(deckId, item.id, token)
      setItems((current) => current.map((entry) => (entry.id === updated.id ? updated : entry)))
      setDrafts((current) => {
        const next = { ...current }
        delete next[item.id]
        return next
      })
    } catch (caught) {
      toaster.error({
        title: "Could not regenerate",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    }
  }

  async function remove(item: DeckItem) {
    if (!token) return
    try {
      await api.deleteDeckItem(deckId, item.id, token)
      setItems((current) => current.filter((entry) => entry.id !== item.id))
      setTotal((value) => Math.max(0, value - 1))
      setDrafts((current) => {
        const next = { ...current }
        delete next[item.id]
        return next
      })
      toaster.success({ title: "Question deleted" })
    } catch (caught) {
      toaster.error({
        title: "Could not delete",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    }
  }

  async function publish() {
    if (!token) return
    try {
      await api.publishDeck(deckId, token)
      toaster.success({ title: "Deck published" })
      await loadDeck()
    } catch (caught) {
      toaster.error({
        title: "Could not publish",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    }
  }

  async function addQuestion(payload: { front: string; reading: string; meaning: string }) {
    if (!token) return
    try {
      const created = await api.createDeckItem(deckId, payload, token)
      setPage(1)
      setFilter("all")
      setSearch("")
      await Promise.all([loadDeck(), loadItems()])
      toaster.success({ title: "Question added", description: `${created.front} → ${created.reading}` })
    } catch (caught) {
      toaster.error({
        title: "Could not add the question",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
      throw caught
    }
  }

  function updateLocalItem(itemId: number, patch: DeckItemUpdate & Partial<DeckItem>) {
    setItems((current) =>
      current.map((entry) => (entry.id === itemId ? { ...entry, ...patch } : entry)),
    )
  }

  if (error) {
    return (
      <Stack gap="6">
        <BackLink />
        <Card.Root bg="bg.panel" borderColor="border.muted">
          <Card.Body>
            <Text color="fg.error">{error}</Text>
          </Card.Body>
        </Card.Root>
      </Stack>
    )
  }

  const deck = detail?.deck
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <Stack gap="8">
      <Stack gap="4">
        <BackLink />
        <Flex justify="space-between" align="end" gap="4" wrap="wrap">
          <Stack gap="1">
            <Flex align="center" gap="3" wrap="wrap">
              <Heading as="h1" size="2xl" letterSpacing="-0.02em">
                {deck?.title ?? "Deck"}
              </Heading>
              {deck ? (
                <Badge
                  colorPalette={deck.status === "ready" ? "green" : "orange"}
                  variant="subtle"
                  rounded="full"
                  px="2.5"
                  py="1"
                >
                  {deck.status === "ready" ? "Ready" : "Draft"}
                </Badge>
              ) : null}
            </Flex>
            <Text fontSize="sm" color="fg.muted">
              {deck
                ? `${deck.total_items} questions · ${deck.quiz_ready} ready · ${deck.needs_review} need review · accuracy ${formatPercent(deck.accuracy)}`
                : "Loading…"}
            </Text>
          </Stack>

          <Flex gap="2" wrap="wrap">
            <Button variant="surface" colorPalette="gray" onClick={() => setAddOpen(true)}>
              <LuCirclePlus />
              Add question
            </Button>
            <Button
              variant="surface"
              colorPalette="gray"
              onClick={saveChanges}
              disabled={dirtyCount === 0}
              loading={saving}
            >
              <LuSave />
              Save changes{dirtyCount ? ` (${dirtyCount})` : ""}
            </Button>
            {deck?.status === "ready" ? (
              <Button colorPalette="brand" onClick={() => navigate(`/decks/${deckId}/quiz`)}>
                <LuPlay />
                Start quiz
              </Button>
            ) : (
              <Button
                colorPalette="brand"
                onClick={publish}
                disabled={!deck || deck.quiz_ready === 0}
              >
                Publish deck
              </Button>
            )}
          </Flex>
        </Flex>
      </Stack>

      {detail ? (
        <>
          <Collapsible.Root open={showReport} onOpenChange={(state) => setShowReport(state.open)}>
            <Collapsible.Trigger asChild>
              <Button variant="ghost" colorPalette="gray" size="sm" px="2" alignSelf="start">
                {showReport ? <LuChevronDown /> : <LuChevronRight />}
                Import report
              </Button>
            </Collapsible.Trigger>
            <Collapsible.Content>
              <Box pt="3">
                <DeckReport report={detail.report as ImportReport} />
              </Box>
            </Collapsible.Content>
          </Collapsible.Root>

          <Stack gap="4">
            <Flex gap="3" wrap="wrap" align="center" justify="space-between">
              <Flex gap="2" wrap="wrap">
                {FILTERS.map((entry) => (
                  <Button
                    key={entry.value}
                    size="xs"
                    variant={filter === entry.value ? "solid" : "surface"}
                    colorPalette={filter === entry.value ? "brand" : "gray"}
                    onClick={() => setFilter(entry.value)}
                  >
                    {entry.label}
                  </Button>
                ))}
              </Flex>
              <Flex align="center" gap="2" minW="56">
                <LuSearch size={14} />
                <Input
                  size="sm"
                  placeholder="Search prompt, reading or translation"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value)
                    setPage(1)
                  }}
                />
              </Flex>
            </Flex>

            {loading ? (
              <Stack gap="2">
                <Skeleton height="14" rounded="md" />
                <Skeleton height="14" rounded="md" />
                <Skeleton height="14" rounded="md" />
              </Stack>
            ) : items.length === 0 ? (
              <Center py="16" color="fg.muted">
                <Text fontSize="sm">No questions match this filter.</Text>
              </Center>
            ) : (
              <Card.Root bg="bg.panel" borderColor="border.muted">
                <Card.Body p="0">
                  <Table.ScrollArea>
                    <Table.Root size="sm" variant="line" interactive>
                      <Table.Header>
                        <Table.Row>
                          <Table.ColumnHeader w="36">Prompt</Table.ColumnHeader>
                          <Table.ColumnHeader w="44">Reading</Table.ColumnHeader>
                          <Table.ColumnHeader>Translation</Table.ColumnHeader>
                          <Table.ColumnHeader minW="64">Answers</Table.ColumnHeader>
                          <Table.ColumnHeader w="24" textAlign="end">
                            Actions
                          </Table.ColumnHeader>
                        </Table.Row>
                      </Table.Header>
                      <Table.Body>
                        {items.map((item) => (
                          <ItemRow
                            key={item.id}
                            item={item}
                            draft={drafts[item.id]}
                            onChange={(patch) => {
                              applyDraft(item.id, patch)
                              updateLocalItem(item.id, patch)
                            }}
                            onRegenerate={() => regenerate(item)}
                            onDelete={() => remove(item)}
                          />
                        ))}
                      </Table.Body>
                    </Table.Root>
                  </Table.ScrollArea>
                </Card.Body>
              </Card.Root>
            )}

            {totalPages > 1 ? (
              <Flex justify="space-between" align="center" gap="4">
                <Text fontSize="xs" color="fg.subtle">
                  {total} questions
                </Text>
                <Flex align="center" gap="1">
                  <IconButton
                    variant="ghost"
                    size="sm"
                    aria-label="Previous page"
                    disabled={page === 1}
                    onClick={() => setPage((value) => Math.max(1, value - 1))}
                  >
                    <LuArrowLeft />
                  </IconButton>
                  <Text fontSize="sm" minW="24" textAlign="center">
                    Page {page} of {totalPages}
                  </Text>
                  <IconButton
                    variant="ghost"
                    size="sm"
                    aria-label="Next page"
                    disabled={page === totalPages}
                    onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                  >
                    <LuChevronRight />
                  </IconButton>
                </Flex>
              </Flex>
            ) : null}
          </Stack>
        </>
      ) : (
        <Center py="20">
          <Spinner color="brand.fg" />
        </Center>
      )}

      <AddQuestionDialog open={addOpen} onOpenChange={setAddOpen} onSubmit={addQuestion} />
    </Stack>
  )
}

function BackLink() {
  return (
    <RouterLink to="/decks" style={{ alignSelf: "flex-start" }}>
      <Flex align="center" gap="1.5" fontSize="sm" color="fg.muted">
        <LuArrowLeft size={13} />
        All decks
      </Flex>
    </RouterLink>
  )
}

interface ItemRowProps {
  item: DeckItem
  draft?: DeckItemUpdate
  onChange: (patch: DeckItemUpdate) => void
  onRegenerate: () => void
  onDelete: () => void
}

function ItemRow({ item, draft, onChange, onRegenerate, onDelete }: ItemRowProps) {
  const reading = draft?.reading ?? item.reading
  const options = draft?.options ?? item.options
  const correctIndex = draft?.correct_index ?? item.correct_index
  const hidden = draft?.hidden ?? item.hidden
  const needsReview = draft?.needs_review ?? item.needs_review
  const [editingOptions, setEditingOptions] = React.useState(false)

  return (
    <Table.Row opacity={hidden ? 0.55 : 1}>
      <Table.Cell verticalAlign="top">
        <Input
          size="sm"
          value={draft?.front ?? item.front}
          onChange={(event) => onChange({ front: event.target.value })}
          fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
        />
        <Flex gap="2" mt="1.5">
          {needsReview ? (
            <Badge colorPalette="orange" variant="subtle" rounded="full" fontSize="2xs">
              Review
            </Badge>
          ) : null}
          {hidden ? (
            <Badge colorPalette="gray" variant="subtle" rounded="full" fontSize="2xs">
              Hidden
            </Badge>
          ) : null}
        </Flex>
      </Table.Cell>

      <Table.Cell verticalAlign="top">
        <Input
          size="sm"
          value={reading}
          onChange={(event) => onChange({ reading: event.target.value })}
          fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
        />
      </Table.Cell>

      <Table.Cell verticalAlign="top">
        <Textarea
          size="sm"
          rows={2}
          value={draft?.meaning ?? item.meaning}
          onChange={(event) => onChange({ meaning: event.target.value })}
        />
      </Table.Cell>

      <Table.Cell verticalAlign="top">
        <Stack gap="1.5">
          {editingOptions ? (
            <>
              {options.map((option, index) => (
                <Flex key={index} align="center" gap="2">
                  <Checkbox.Root
                    checked={index === correctIndex}
                    onCheckedChange={() => onChange({ correct_index: index })}
                    size="sm"
                  >
                    <Checkbox.HiddenInput />
                    <Checkbox.Control />
                  </Checkbox.Root>
                  <Input
                    size="xs"
                    value={option}
                    onChange={(event) => {
                      const next = [...options]
                      next[index] = event.target.value
                      onChange({ options: next, correct_index: correctIndex })
                    }}
                  />
                </Flex>
              ))}
              <Button size="2xs" variant="ghost" colorPalette="gray" onClick={() => setEditingOptions(false)}>
                Done
              </Button>
            </>
          ) : (
            <>
              <Flex gap="1.5" wrap="wrap">
                {options.map((option, index) => (
                  <Badge
                    key={index}
                    variant="subtle"
                    colorPalette={index === correctIndex ? "green" : "gray"}
                    rounded="full"
                    px="2"
                    py="0.5"
                    fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
                  >
                    {option}
                  </Badge>
                ))}
              </Flex>
              <Button size="2xs" variant="ghost" colorPalette="gray" onClick={() => setEditingOptions(true)}>
                Edit answers
              </Button>
            </>
          )}
        </Stack>
      </Table.Cell>

      <Table.Cell verticalAlign="top" textAlign="end">
        <Flex gap="1" justify="flex-end">
          <IconButton
            size="2xs"
            variant="ghost"
            aria-label="Regenerate answers"
            title="Regenerate answers"
            onClick={onRegenerate}
          >
            <LuRefreshCw />
          </IconButton>
          <IconButton
            size="2xs"
            variant="ghost"
            aria-label={hidden ? "Show question" : "Hide question"}
            title={hidden ? "Show question" : "Hide question"}
            onClick={() => onChange({ hidden: !hidden })}
          >
            {hidden ? <LuEye /> : <LuEyeOff />}
          </IconButton>
          <IconButton
            size="2xs"
            variant="ghost"
            colorPalette="red"
            aria-label="Delete question"
            title="Delete question"
            onClick={onDelete}
          >
            <LuTrash2 />
          </IconButton>
        </Flex>
        {needsReview ? (
          <Button
            size="2xs"
            variant="surface"
            colorPalette="orange"
            mt="2"
            onClick={() => onChange({ needs_review: false })}
          >
            Mark reviewed
          </Button>
        ) : null}
      </Table.Cell>
    </Table.Row>
  )
}
