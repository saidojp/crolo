import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Center,
  Flex,
  Heading,
  Kbd,
  Progress,
  RadioCard,
  SimpleGrid,
  Spinner,
  Stack,
  Text,
} from "@chakra-ui/react"
import * as React from "react"
import {
  LuArrowLeft,
  LuArrowRight,
  LuCheck,
  LuCircleCheck,
  LuCircleX,
  LuPlay,
  LuX,
} from "react-icons/lu"
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from "react-router-dom"

import { KanjiPrompt, Reading } from "@/components/kanji"
import { toaster } from "@/components/ui/toaster"
import { useAuth } from "@/auth/AuthProvider"
import {
  ApiError,
  type AnswerResult,
  type DeckSummary,
  type SessionState,
  api,
} from "@/lib/api"

type Mode = "instant" | "end"
type Source = "all" | "unseen" | "weak"

const COUNTS = [10, 20, 50, 0]

export function QuizPage() {
  const { deckId: deckIdParam } = useParams()
  const deckId = Number(deckIdParam)
  const { token } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const sessionParam = Number(searchParams.get("session"))
  const retryParam = searchParams.get("retry")
  const [retryIds] = React.useState<number[] | null>(() => {
    if (!retryParam) return null
    const parsed = retryParam
      .split(",")
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value > 0)
    return parsed.length ? parsed : null
  })
  const [deck, setDeck] = React.useState<DeckSummary | null>(null)
  const [session, setSession] = React.useState<SessionState | null>(null)
  const [bootstrapping, setBootstrapping] = React.useState(true)
  const [error, setError] = React.useState<string | null>(null)

  // Setup form state.
  const [mode, setMode] = React.useState<Mode>("instant")
  const [source, setSource] = React.useState<Source>("all")
  const [count, setCount] = React.useState<number>(20)
  const [starting, setStarting] = React.useState(false)

  React.useEffect(() => {
    if (!token || !Number.isFinite(deckId)) return
    let cancelled = false
    setBootstrapping(true)
    Promise.all([
      api.getDeck(deckId, token),
      Number.isFinite(sessionParam) && sessionParam > 0
        ? api.getSession(sessionParam, token)
        : Promise.resolve(null),
    ])
      .then(([detail, loadedSession]) => {
        if (cancelled) return
        setDeck(detail.deck)
        if (loadedSession) setSession(loadedSession)
        if (retryIds) {
          setCount(retryIds.length)
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.detail : "Could not load the quiz")
        }
      })
      .finally(() => {
        if (!cancelled) setBootstrapping(false)
      })
    return () => {
      cancelled = true
    }
  }, [deckId, token, sessionParam])

  async function start() {
    if (!token) return
    setStarting(true)
    setError(null)
    try {
      const started = await api.startSession(
        deckId,
        {
          mode,
          source,
          count: retryIds ? undefined : count === 0 ? undefined : count,
          itemIds: retryIds ?? undefined,
        },
        token,
      )
      setSession(started)
      setSearchParams({ session: String(started.id) }, { replace: true })
    } catch (caught) {
      const message = caught instanceof ApiError ? caught.detail : "Could not start the quiz"
      setError(message)
      toaster.error({ title: "Could not start", description: message })
    } finally {
      setStarting(false)
    }
  }
  function leave() {
    setSession(null)
    setSearchParams({}, { replace: true })
  }

  if (bootstrapping) {
    return (
      <Center py="24">
        <Spinner color="brand.fg" />
      </Center>
    )
  }

  if (error && !session) {
    return (
      <Stack gap="6">
        <BackLink deckId={deckId} />
        <Alert.Root status="error">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>Something went wrong</Alert.Title>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert.Root>
      </Stack>
    )
  }

  if (!session) {
    return (
      <Stack gap="8" maxW="3xl">
        <BackLink deckId={deckId} />
        <Stack gap="2">
          <Heading as="h1" size="2xl" letterSpacing="-0.02em">
            {deck?.title ?? "Quiz"}
          </Heading>
          <Text color="fg.muted">
            {retryIds
              ? `Retrying ${retryIds.length} question${retryIds.length === 1 ? "" : "s"} from your last session.`
              : "Choose how you want to practise. Only the reading is tested; the translation appears as a hint."}
          </Text>
        </Stack>

        <Card.Root bg="bg.panel" borderColor="border.muted">
          <Card.Body>
            <Stack gap="7">
              <Stack gap="3">
                <Text fontSize="sm" fontWeight="medium">
                  Feedback
                </Text>
                <RadioCard.Root
                  value={mode}
                  onValueChange={(details) => setMode(details.value as Mode)}
                >
                  <SimpleGrid columns={{ base: 1, sm: 2 }} gap="3">
                    <RadioCard.Item value="instant">
                      <RadioCard.ItemHiddenInput />
                      <RadioCard.ItemControl>
                        <RadioCard.ItemContent>
                          <RadioCard.ItemText>Instant feedback</RadioCard.ItemText>
                          <RadioCard.ItemDescription>
                            See whether you were right after every answer.
                          </RadioCard.ItemDescription>
                        </RadioCard.ItemContent>
                        <RadioCard.ItemIndicator />
                      </RadioCard.ItemControl>
                    </RadioCard.Item>
                    <RadioCard.Item value="end">
                      <RadioCard.ItemHiddenInput />
                      <RadioCard.ItemControl>
                        <RadioCard.ItemContent>
                          <RadioCard.ItemText>Answers at the end</RadioCard.ItemText>
                          <RadioCard.ItemDescription>
                            Answer everything first, then review all results.
                          </RadioCard.ItemDescription>
                        </RadioCard.ItemContent>
                        <RadioCard.ItemIndicator />
                      </RadioCard.ItemControl>
                    </RadioCard.Item>
                  </SimpleGrid>
                </RadioCard.Root>
              </Stack>

              <Stack gap="3">
                <Text fontSize="sm" fontWeight="medium">
                  Questions
                </Text>
                <SimpleGrid columns={{ base: 2, sm: 4 }} gap="2">
                  {(
                    [
                      ["all", "All"],
                      ["unseen", "Unseen"],
                      ["weak", "Weak"],
                    ] as Array<[Source, string]>
                  ).map(([value, label]) => (
                    <Button
                      key={value}
                      size="sm"
                      variant={source === value ? "solid" : "surface"}
                      colorPalette={source === value ? "brand" : "gray"}
                      onClick={() => setSource(value)}
                    >
                      {label}
                    </Button>
                  ))}
                </SimpleGrid>
                <Text fontSize="xs" color="fg.subtle">
                  Unseen uses cards you have not answered yet; weak picks cards where your accuracy is
                  70% or lower.
                </Text>
              </Stack>

              <Stack gap="3">
                <Text fontSize="sm" fontWeight="medium">
                  Session length
                </Text>
                <Flex gap="2" wrap="wrap">
                  {COUNTS.map((value) => (
                    <Button
                      key={value}
                      size="sm"
                      variant={count === value ? "solid" : "surface"}
                      colorPalette={count === value ? "brand" : "gray"}
                      onClick={() => setCount(value)}
                    >
                      {value === 0 ? "All" : value}
                    </Button>
                  ))}
                </Flex>
              </Stack>

              <Button colorPalette="brand" size="lg" onClick={start} loading={starting}>
                <LuPlay />
                Start session
              </Button>
            </Stack>
          </Card.Body>
        </Card.Root>
      </Stack>
    )
  }

  return (
    <QuizRunner
      session={session}
      onSessionChange={setSession}
      onLeave={leave}
      onFinished={(finished) => navigate(`/sessions/${finished.id}/results`)}
    />
  )
}

function BackLink({ deckId }: { deckId: number }) {
  return (
    <RouterLink to={`/decks/${deckId}`} style={{ alignSelf: "flex-start" }}>
      <Flex align="center" gap="1.5" fontSize="sm" color="fg.muted">
        <LuArrowLeft size={13} />
        Back to deck
      </Flex>
    </RouterLink>
  )
}

interface RunnerProps {
  session: SessionState
  onSessionChange: (session: SessionState) => void
  onLeave: () => void
  onFinished: (session: SessionState) => void
}

function QuizRunner({ session, onSessionChange, onLeave, onFinished }: RunnerProps) {
  const { token } = useAuth()
  const [index, setIndex] = React.useState(() => {
    const firstUnanswered = session.items.findIndex((item) => item.selected_index === null)
    return firstUnanswered === -1 ? session.items.length - 1 : firstUnanswered
  })
  const [answer, setAnswer] = React.useState<AnswerResult | null>(null)
  const [pending, setPending] = React.useState(false)
  const [finishing, setFinishing] = React.useState(false)

  const item = session.items[index]
  const isEndMode = session.mode === "end"
  const revealed = isEndMode
    ? false
    : item.selected_index !== null || answer?.item_id === item.id
  // In end mode the choice lives on the session item so navigating back keeps it.
  const chosenIndex = item.selected_index
  const feedback = answer?.item_id === item.id ? answer : null

  const answeredCount = session.items.filter((entry) => entry.selected_index !== null).length
  const progress = (answeredCount / session.total) * 100

  async function choose(optionIndex: number) {
    if (!token || pending || isFinished) return
    if (revealed) return
    if (isEndMode && item.selected_index === optionIndex) {
      // Tapping the chosen option again clears it.
      onSessionChange({
        ...session,
        answered: session.items.filter(
          (entry) => entry.id !== item.id && entry.selected_index !== null,
        ).length,
        items: session.items.map((entry) =>
          entry.id === item.id ? { ...entry, selected_index: null } : entry,
        ),
      })
      return
    }

    if (isEndMode) {
      onSessionChange({
        ...session,
        answered: session.items.filter(
          (entry) => entry.id === item.id || entry.selected_index !== null,
        ).length,
        items: session.items.map((entry) =>
          entry.id === item.id ? { ...entry, selected_index: optionIndex } : entry,
        ),
      })
      return
    }

    setPending(true)
    try {
      const result = await api.answerSessionItem(session.id, item.id, optionIndex, token)
      setAnswer(result)
      onSessionChange({
        ...session,
        answered: result.answered,
        correct: result.correct_count,
        items: session.items.map((entry) =>
          entry.id === item.id
            ? {
                ...entry,
                selected_index: optionIndex,
                is_correct: result.correct,
                reading: result.reading,
                meaning: result.meaning,
                correct_index: result.correct_index,
              }
            : entry,
        ),
      })
    } catch (caught) {
      toaster.error({
        title: "Could not submit the answer",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    } finally {
      setPending(false)
    }
  }

  function next() {
    setAnswer(null)
    setIndex((value) => Math.min(session.items.length - 1, value + 1))
  }

  function previous() {
    setAnswer(null)
    setIndex((value) => Math.max(0, value - 1))
  }

  async function finish() {
    if (!token) return
    setFinishing(true)
    try {
      let current = session
      if (isEndMode) {
        const answers = session.items
          .filter((entry) => entry.selected_index !== null)
          .map((entry) => ({
            item_id: entry.id,
            selected_index: entry.selected_index as number,
          }))
        if (answers.length !== session.total) {
          toaster.error({ title: "Answer every question before finishing" })
          return
        }
        current = await api.submitSessionAnswers(session.id, answers, token)
        onSessionChange(current)
      }
      const finished = await api.finishSession(session.id, token)
      onFinished(finished)
    } catch (caught) {
      toaster.error({
        title: "Could not finish the session",
        description: caught instanceof ApiError ? caught.detail : "Unexpected error",
      })
    } finally {
      setFinishing(false)
    }
  }

  // Keyboard: 1-4 select, Enter advances.
  React.useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return

      if (/^[1-4]$/.test(event.key)) {
        const optionIndex = Number(event.key) - 1
        if (optionIndex < item.options.length) {
          event.preventDefault()
          void choose(optionIndex)
        }
      }
      if (event.key === "Enter" && revealed) {
        event.preventDefault()
        if (index < session.items.length - 1) {
          next()
        } else {
          void finish()
        }
      }
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  })

  const isLast = index === session.items.length - 1
  const isFinished = session.status === "finished"
  const canAdvance = isEndMode ? chosenIndex !== null : revealed

  return (
    <Stack gap="6" maxW="3xl" mx="auto">
      <Flex justify="space-between" align="center" gap="4">
        <Button variant="ghost" colorPalette="gray" size="sm" onClick={onLeave}>
          <LuX />
          Exit
        </Button>
        <Flex align="center" gap="3" fontSize="sm" color="fg.muted">
          <Text>
            {index + 1} / {session.total}
          </Text>
          <Badge variant="subtle" colorPalette="gray" rounded="full">
            {isEndMode ? "Answers at the end" : "Instant feedback"}
          </Badge>
        </Flex>
      </Flex>

      <Progress.Root value={progress} size="xs">
        <Progress.Track>
          <Progress.Range />
        </Progress.Track>
      </Progress.Root>

      <Card.Root bg="bg.panel" borderColor="border.muted">
        <Card.Body px={{ base: "5", md: "10" }} py={{ base: "8", md: "12" }}>
          <Stack gap="8" align="stretch">
            <Center minH="28">
              <KanjiPrompt size="2xl" textAlign="center">
                {item.front}
              </KanjiPrompt>
            </Center>

            <SimpleGrid columns={{ base: 1, sm: 2 }} gap="3">
              {item.options.map((option, optionIndex) => {
                const isChosen = chosenIndex === optionIndex
                const correctIndex = feedback?.correct_index ?? item.correct_index
                const isCorrectOption = revealed && correctIndex === optionIndex
                const isWrongChoice = revealed && isChosen && !isCorrectOption

                return (
                  <Button
                    key={`${option}-${optionIndex}`}
                    variant="outline"
                    size="lg"
                    h="14"
                    justifyContent="flex-start"
                    borderColor={
                      isCorrectOption
                        ? "border.success"
                        : isWrongChoice
                          ? "border.error"
                          : isChosen
                            ? "brand.border"
                            : "border.emphasized"
                    }
                    bg={
                      isCorrectOption
                        ? "bg.success"
                        : isWrongChoice
                          ? "bg.error"
                          : isChosen
                            ? "bg.muted"
                            : "transparent"
                    }
                    onClick={() => choose(optionIndex)}
                    aria-disabled={revealed || pending}
                    aria-pressed={isChosen}
                    cursor={revealed || pending ? "default" : "pointer"}
                  >
                    <Flex align="center" gap="3" w="full">
                      <Kbd size="sm">{optionIndex + 1}</Kbd>
                      <Reading fontSize="xl" lineHeight="1">
                        {option}
                      </Reading>
                      <Box ml="auto">
                        {isCorrectOption ? <LuCircleCheck color="var(--chakra-colors-green-400)" /> : null}
                        {isWrongChoice ? <LuCircleX color="var(--chakra-colors-red-400)" /> : null}
                      </Box>
                    </Flex>
                  </Button>
                )
              })}
            </SimpleGrid>

            {revealed && feedback ? (
              <Box
                borderWidth="1px"
                rounded="md"
                px="4"
                py="3"
                bg={feedback.correct ? "bg.success" : "bg.error"}
                borderColor={feedback.correct ? "border.success" : "border.error"}
              >
                <Stack gap="1">
                  <Flex align="center" gap="2">
                    {feedback.correct ? (
                      <LuCircleCheck size={15} color="var(--chakra-colors-green-400)" />
                    ) : (
                      <LuCircleX size={15} color="var(--chakra-colors-red-400)" />
                    )}
                    <Text fontSize="sm" fontWeight="medium">
                      {feedback.correct ? "Correct" : "Not quite"}
                    </Text>
                  </Flex>
                  <Flex gap="3" align="baseline" wrap="wrap">
                      <Reading fontSize="sm" color="fg.muted">
                        {feedback.reading}
                      </Reading>
                    {feedback.meaning ? (
                      <Text fontSize="sm" color="fg.muted">
                        {feedback.meaning}
                      </Text>
                    ) : null}
                  </Flex>
                </Stack>
              </Box>
            ) : null}

            <Flex justify="space-between" gap="3" align="center">
              <Button
                variant="ghost"
                colorPalette="gray"
                onClick={previous}
                disabled={index === 0}
              >
                <LuArrowLeft />
                Back
              </Button>

              {isEndMode ? (
                isLast ? (
                  <Button colorPalette="brand" onClick={finish} loading={finishing}>
                    Finish session
                    <LuCheck />
                  </Button>
                ) : (
                  <Button
                    colorPalette="brand"
                    variant="surface"
                    onClick={next}
                    disabled={!canAdvance && index === session.items.length - 1}
                  >
                    Next
                    <LuArrowRight />
                  </Button>
                )
              ) : isLast && revealed ? (
                <Button colorPalette="brand" onClick={finish} loading={finishing}>
                  See results
                  <LuArrowRight />
                </Button>
              ) : (
                <Button colorPalette="brand" onClick={next} disabled={!canAdvance}>
                  Next
                  <LuArrowRight />
                </Button>
              )}
            </Flex>
          </Stack>
        </Card.Body>
      </Card.Root>

      <Text fontSize="xs" color="fg.subtle" textAlign="center">
        Press <Kbd size="sm">1</Kbd>–<Kbd size="sm">4</Kbd> to answer, <Kbd size="sm">Enter</Kbd> to
        continue.
      </Text>
    </Stack>
  )
}
