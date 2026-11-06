import {
  Button,
  Dialog,
  Field,
  Input,
  Portal,
  Stack,
  Textarea,
} from "@chakra-ui/react"
import * as React from "react"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (payload: { front: string; reading: string; meaning: string }) => Promise<void>
}

/** Small modal for adding one question by hand. */
export function AddQuestionDialog({ open, onOpenChange, onSubmit }: Props) {
  const [front, setFront] = React.useState("")
  const [reading, setReading] = React.useState("")
  const [meaning, setMeaning] = React.useState("")
  const [pending, setPending] = React.useState(false)

  React.useEffect(() => {
    if (open) {
      setFront("")
      setReading("")
      setMeaning("")
    }
  }, [open])

  const canSubmit = front.trim() !== "" && reading.trim() !== "" && !pending

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    setPending(true)
    try {
      await onSubmit({ front: front.trim(), reading: reading.trim(), meaning: meaning.trim() })
      onOpenChange(false)
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={(details) => onOpenChange(details.open)}>
      <Portal>
        <Dialog.Backdrop />
        <Dialog.Positioner>
          <Dialog.Content as="form" onSubmit={submit}>
            <Dialog.Header>
              <Dialog.Title>Add a question</Dialog.Title>
            </Dialog.Header>
            <Dialog.Body>
              <Stack gap="4">
                <Field.Root>
                  <Field.Label>Prompt (kanji)</Field.Label>
                  <Input
                    value={front}
                    onChange={(event) => setFront(event.target.value)}
                    placeholder="経済"
                    fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
                    required
                  />
                </Field.Root>
                <Field.Root>
                  <Field.Label>Reading (hiragana)</Field.Label>
                  <Input
                    value={reading}
                    onChange={(event) => setReading(event.target.value)}
                    placeholder="けいざい"
                    fontFamily='"Hiragino Sans", "Yu Gothic", system-ui, sans-serif'
                    required
                  />
                </Field.Root>
                <Field.Root>
                  <Field.Label>Translation</Field.Label>
                  <Textarea
                    value={meaning}
                    onChange={(event) => setMeaning(event.target.value)}
                    placeholder="economy"
                    rows={2}
                  />
                </Field.Root>
              </Stack>
            </Dialog.Body>
            <Dialog.Footer>
              <Dialog.ActionTrigger asChild>
                <Button variant="ghost" colorPalette="gray">
                  Cancel
                </Button>
              </Dialog.ActionTrigger>
              <Button type="submit" colorPalette="brand" loading={pending} disabled={!canSubmit}>
                Add question
              </Button>
            </Dialog.Footer>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  )
}
