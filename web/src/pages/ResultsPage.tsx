import {
  Badge,
  Box,
  Button,
  Card,
  Center,
  Flex,
  Heading,
  SimpleGrid,
  Spinner,
  Stack,
  Table,
  Text,
} from "@chakra-ui/react"
import * as React from "react"
import { LuArrowLeft, LuCircleCheck, LuCircleX, LuPlay, LuRotateCcw } from "react-icons/lu"
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom"

import { KanjiPrompt, Reading } from "@/components/kanji"
import { useAuth } from "@/auth/AuthProvider"
import { ApiError, type SessionState, api } from "@/lib/api"

export function ResultsPage() {
  const { sessionId: sessionIdParam } = useParams()
  const sessionId = Number(sessionIdParam)
  const { token } = useAuth()
  const navigate = useNavigate()
  const [session, setSession] = React.useState<SessionState | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [filter, setFilter] = React.useState<"all" | "wrong">("all")

  React.useEffect(() => {
    if (!token || !Number.isFinite(sessionId)) return
    let cancelled = false
    api
      .getSession(sessionId, token)
      .then((loaded) => {
        if (!cancelled) setSession(loaded)
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.detail : "Could not load the results")
        }
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, token])

  if (error) {
    return (
      <Stack gap="6">
        <Text color="fg.error">{error}</Text>
      </Stack>
    )
  }

  if (!session) {
    return (
      <Center py="24">
        <Spinner color="brand.fg" />
      </Center>
    )
  }

  const total = session.items.length
  const correct = session.items.filter((item) => item.is_correct).length
  const wrongItems = session.items.filter((item) => item.is_correct === false)
  const percent = total ? Math.round((correct / total) * 100) : 0
  const visible = filter === "wrong" ? wrongItems : session.items

  return (
    <Stack gap="8" maxW="4xl" mx="auto">
      <Flex justify="space-between" align="center" gap="4" wrap="wrap">
        <RouterLink to={`/decks/${session.deck_id}`}>
          <Flex align="center" gap="1.5" fontSize="sm" color="fg.muted">
            <LuArrowLeft size={13} />
            {session.deck_title}
          </Flex>
        </RouterLink>
        <Badge variant="subtle" colorPalette="gray" rounded="full">
          {session.mode === "end" ? "Answers at the end" : "Instant feedback"}
        </Badge>
      </Flex>

      <Stack gap="2">
        <Heading as="h1" size="2xl" letterSpacing="-0.02em">
          {percent >= 80 ? "Nicely done" : percent >= 50 ? "Getting there" : "Keep practising"}
        </Heading>
        <Text color="fg.muted">
          {correct} of {total} correct on this run.
        </Text>
      </Stack>

      <SimpleGrid columns={{ base: 1, sm: 3 }} gap="4">
        <SummaryCard label="Score" value={`${percent}%`} />
        <SummaryCard label="Correct" value={String(correct)} success />
        <SummaryCard label="Incorrect" value={String(total - correct)} error={total - correct > 0} />
      </SimpleGrid>

      <Flex gap="2" wrap="wrap">
        <Button
          size="sm"
          variant={filter === "all" ? "solid" : "surface"}
          colorPalette={filter === "all" ? "brand" : "gray"}
          onClick={() => setFilter("all")}
        >
          All answers
        </Button>
        <Button
          size="sm"
          variant={filter === "wrong" ? "solid" : "surface"}
          colorPalette={filter === "wrong" ? "brand" : "gray"}
          onClick={() => setFilter("wrong")}
          disabled={wrongItems.length === 0}
        >
          Mistakes ({wrongItems.length})
        </Button>
        <Box flex="1" />
        {wrongItems.length > 0 ? (
          <Button
            size="sm"
            colorPalette="brand"
            onClick={() => {
              const ids = wrongItems
                .map((item) => item.item_id)
                .filter((value): value is number => value !== null)
              if (ids.length === 0) return
              navigate(`/decks/${session.deck_id}/quiz?retry=${ids.join(",")}`)
            }}
          >
            <LuRotateCcw />
            Retry mistakes ({wrongItems.length})
          </Button>
        ) : (
          <Button
            size="sm"
            colorPalette="brand"
            onClick={() => navigate(`/decks/${session.deck_id}/quiz`)}
          >
            <LuPlay />
            New session
          </Button>
        )}
      </Flex>

      <Card.Root bg="bg.panel" borderColor="border.muted">
        <Card.Body p="0">
          <Table.ScrollArea>
            <Table.Root size="sm" variant="line">
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader w="28">Prompt</Table.ColumnHeader>
                  <Table.ColumnHeader w="32">Reading</Table.ColumnHeader>
                  <Table.ColumnHeader>Your answer</Table.ColumnHeader>
                  <Table.ColumnHeader w="16" textAlign="end">
                    Result
                  </Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {visible.map((item) => {
                  const selected = item.selected_index
                  const selectedText =
                    selected !== null && selected !== undefined ? item.options[selected] : "—"
                  const correctText =
                    item.correct_index !== null && item.correct_index !== undefined
                      ? item.options[item.correct_index] ?? item.reading
                      : item.reading
                  return (
                    <Table.Row key={item.id}>
                      <Table.Cell verticalAlign="top">
                        <KanjiPrompt size="sm">{item.front}</KanjiPrompt>
                      </Table.Cell>
                      <Table.Cell verticalAlign="top">
                        <Reading fontSize="sm">{item.reading ?? correctText}</Reading>
                        {item.meaning ? (
                          <Text fontSize="xs" color="fg.subtle" mt="1">
                            {item.meaning}
                          </Text>
                        ) : null}
                      </Table.Cell>
                      <Table.Cell verticalAlign="top">
                        <Stack gap="0.5">
                          <Text
                            fontSize="sm"
                            color={item.is_correct ? "fg.muted" : "fg.error"}
                            fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
                          >
                            {selectedText}
                          </Text>
                          {item.is_correct === false ? (
                            <Text fontSize="xs" color="fg.subtle">
                              Correct: {correctText}
                            </Text>
                          ) : null}
                        </Stack>
                      </Table.Cell>
                      <Table.Cell verticalAlign="top" textAlign="end">
                        <Flex justify="flex-end">
                          {item.is_correct ? (
                            <LuCircleCheck color="var(--chakra-colors-green-400)" />
                          ) : (
                            <LuCircleX color="var(--chakra-colors-red-400)" />
                          )}
                        </Flex>
                      </Table.Cell>
                    </Table.Row>
                  )
                })}
              </Table.Body>
            </Table.Root>
          </Table.ScrollArea>
        </Card.Body>
      </Card.Root>
    </Stack>
  )
}

function SummaryCard({
  label,
  value,
  success,
  error,
}: {
  label: string
  value: string
  success?: boolean
  error?: boolean
}) {
  return (
    <Card.Root bg="bg.panel" borderColor="border.muted" size="sm">
      <Card.Body>
        <Stack gap="0.5">
          <Text fontSize="xs" color="fg.subtle">
            {label}
          </Text>
          <Text
            fontSize="2xl"
            fontWeight="semibold"
            color={success ? "fg.success" : error ? "fg.error" : "fg"}
          >
            {value}
          </Text>
        </Stack>
      </Card.Body>
    </Card.Root>
  )
}
