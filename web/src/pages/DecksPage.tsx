import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Flex,
  Heading,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
} from "@chakra-ui/react"
import * as React from "react"
import {
  LuCloudUpload,
  LuFileText,
  LuPlay,
  LuRefreshCw,
  LuSettings2,
  LuSparkles,
  LuTriangleAlert,
} from "react-icons/lu"
import { useNavigate } from "react-router-dom"

import { DeckReport } from "@/components/DeckReport"
import { toaster } from "@/components/ui/toaster"
import { useAuth } from "@/auth/AuthProvider"
import { ApiError, type DeckSummary, api } from "@/lib/api"
import { formatDate, formatPercent, pluralize } from "@/lib/format"

export function DecksPage() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [decks, setDecks] = React.useState<DeckSummary[] | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)
  const [uploading, setUploading] = React.useState(false)
  const [dragging, setDragging] = React.useState(false)
  const [report, setReport] = React.useState<
    { deckId: number; title: string; report: import("@/lib/api").ImportReport } | null
  >(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const load = React.useCallback(async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      setDecks(await api.listDecks(token))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : "Could not load decks")
    } finally {
      setLoading(false)
    }
  }, [token])

  React.useEffect(() => {
    void load()
  }, [load])

  async function handleFile(file: File) {
    if (!token) return
    if (!/\.(apkg|colpkg)$/i.test(file.name)) {
      toaster.error({ title: "Choose an .apkg or .colpkg file" })
      return
    }
    setUploading(true)
    try {
      const detail = await api.importDeck(file, token)
      setReport({
        deckId: detail.deck.id,
        title: detail.deck.title,
        report: detail.report,
      })
      toaster.success({
        title: "Deck imported",
        description: `${pluralize(detail.deck.total_items, "question")} generated`,
      })
      await load()
    } catch (caught) {
      toaster.error({
        title: "Import failed",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    } finally {
      setUploading(false)
    }
  }

  function onDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setDragging(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void handleFile(file)
  }

  return (
    <Stack gap="8">
      <Stack gap="3">
        <Text textStyle="xs" color="fg.subtle" letterSpacing="0.14em" textTransform="uppercase">
          Decks
        </Text>
        <Flex justify="space-between" align="end" gap="4" wrap="wrap">
          <Stack gap="1">
            <Heading as="h1" size="2xl" letterSpacing="-0.02em">
              Quiz decks
            </Heading>
            <Text color="fg.muted" maxW="2xl">
              Import an Anki package, review the generated questions, then practise readings.
            </Text>
          </Stack>
          <Button
            colorPalette="brand"
            onClick={() => inputRef.current?.click()}
            loading={uploading}
          >
            <LuCloudUpload />
            Import .apkg
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept=".apkg,.colpkg,application/octet-stream"
            hidden
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleFile(file)
              event.target.value = ""
            }}
          />
        </Flex>
      </Stack>

      <Box
        borderWidth="1px"
        borderStyle="dashed"
        borderColor={dragging ? "brand.border" : "border.emphasized"}
        bg={dragging ? "bg.muted" : "bg.panel"}
        rounded="lg"
        px="6"
        py="8"
        textAlign="center"
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        transition="background 120ms ease, border-color 120ms ease"
      >
        <Stack align="center" gap="2">
          <LuFileText size={20} />
          <Text fontSize="sm" fontWeight="medium">
            Drop an Anki deck here
          </Text>
          <Text fontSize="xs" color="fg.muted">
            Front and Back fields are read automatically. Nothing is uploaded to a third party.
          </Text>
        </Stack>
      </Box>

      {report ? (
        <Card.Root bg="bg.panel" borderColor="border.muted">
          <Card.Header>
            <Flex justify="space-between" align="start" gap="4" wrap="wrap">
              <Stack gap="1">
                <Card.Title fontSize="md">Import report · {report.title}</Card.Title>
                <Card.Description fontSize="sm" color="fg.muted">
                  Review what was parsed before starting a quiz.
                </Card.Description>
              </Stack>
              <Flex gap="2">
                <Button size="sm" variant="surface" colorPalette="gray" onClick={() => setReport(null)}>
                  Dismiss
                </Button>
                <Button
                  size="sm"
                  colorPalette="brand"
                  onClick={() => navigate(`/decks/${report.deckId}`)}
                >
                  Review questions
                </Button>
              </Flex>
            </Flex>
          </Card.Header>
          <Card.Body>
            <DeckReport report={report.report} />
          </Card.Body>
        </Card.Root>
      ) : null}

      {error ? (
        <Alert.Root status="error">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Could not load decks</Alert.Title>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert.Root>
      ) : null}

      {loading && decks === null ? (
        <SimpleGrid columns={{ base: 1, md: 2 }} gap="4">
          <Skeleton height="44" rounded="lg" />
          <Skeleton height="44" rounded="lg" />
        </SimpleGrid>
      ) : decks && decks.length === 0 ? (
        <Stack align="center" gap="3" py="16" color="fg.muted">
          <LuSparkles size={22} />
          <Text fontSize="sm">No decks yet. Import your first .apkg to get started.</Text>
        </Stack>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2 }} gap="4">
          {decks?.map((deck) => (
            <DeckCard key={deck.id} deck={deck} onRefresh={load} />
          ))}
        </SimpleGrid>
      )}
    </Stack>
  )
}

function DeckCard({ deck, onRefresh }: { deck: DeckSummary; onRefresh: () => Promise<void> }) {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [pending, setPending] = React.useState(false)

  async function publish() {
    if (!token) return
    setPending(true)
    try {
      await api.publishDeck(deck.id, token)
      toaster.success({ title: "Deck published" })
      await onRefresh()
    } catch (caught) {
      toaster.error({
        title: "Could not publish",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    } finally {
      setPending(false)
    }
  }

  const needsReview = deck.needs_review > 0
  const draft = deck.status === "draft"

  return (
    <Card.Root bg="bg.panel" borderColor="border.muted" size="sm">
      <Card.Header>
        <Flex justify="space-between" align="start" gap="3">
          <Stack gap="1" minW="0">
            <Card.Title fontSize="md" truncate>
              {deck.title}
            </Card.Title>
            <Card.Description fontSize="xs" color="fg.subtle">
              {deck.source_filename || "Imported deck"} · {formatDate(deck.created_at)}
            </Card.Description>
          </Stack>
          <Badge
            colorPalette={draft ? "orange" : "green"}
            variant="subtle"
            rounded="full"
            px="2.5"
            py="1"
          >
            {draft ? "Draft" : "Ready"}
          </Badge>
        </Flex>
      </Card.Header>

      <Card.Body>
        <Stack gap="4">
          <SimpleGrid columns={3} gap="3">
            <Metric label="Questions" value={String(deck.total_items)} />
            <Metric label="Accuracy" value={formatPercent(deck.accuracy)} />
            <Metric
              label="Sessions"
              value={deck.sessions_completed ? String(deck.sessions_completed) : "—"}
            />
          </SimpleGrid>

          {needsReview ? (
            <Flex align="center" gap="2" color="fg.warning" fontSize="sm">
              <LuTriangleAlert size={14} />
              <Text>
                {pluralize(deck.needs_review, "question")} need a reading decision
              </Text>
            </Flex>
          ) : null}

          <Text fontSize="xs" color="fg.subtle">
            {deck.quiz_ready} ready · {deck.hidden} hidden
            {deck.last_played_at ? ` · last played ${formatDate(deck.last_played_at)}` : ""}
          </Text>
        </Stack>
      </Card.Body>

      <Card.Footer gap="2" flexWrap="wrap">
        <Button size="sm" variant="surface" colorPalette="gray" onClick={() => navigate(`/decks/${deck.id}`)}>
          <LuSettings2 />
          Review
        </Button>
        {draft ? (
          <Button size="sm" colorPalette="brand" onClick={publish} loading={pending}>
            <LuRefreshCw />
            Publish
          </Button>
        ) : (
          <Button size="sm" colorPalette="brand" onClick={() => navigate(`/decks/${deck.id}/quiz`)}>
            <LuPlay />
            Start quiz
          </Button>
        )}
      </Card.Footer>
    </Card.Root>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap="0.5">
      <Text fontSize="xs" color="fg.subtle">
        {label}
      </Text>
      <Text fontSize="lg" fontWeight="semibold">
        {value}
      </Text>
    </Stack>
  )
}
