import {
  Alert,
  Badge,
  Box,
  Flex,
  SimpleGrid,
  Stack,
  Table,
  Text,
} from "@chakra-ui/react"
import type * as React from "react"
import { LuCircleCheck, LuCircleSlash, LuTriangleAlert } from "react-icons/lu"

import { SKIP_REASONS } from "@/lib/format"
import type { ImportReport } from "@/lib/api"

interface Props {
  report: ImportReport
}

/** Import diagnostics: what was parsed, what was skipped and why. */
export function DeckReport({ report }: Props) {
  const skippedEntries = Object.entries(report.skipped).filter(([, count]) => count > 0)
  const skippedTotal = skippedEntries.reduce((sum, [, count]) => sum + count, 0)

  return (
    <Stack gap="5">
      <SimpleGrid columns={{ base: 2, md: 4 }} gap="3">
        <Stat label="Notes read" value={report.total_notes} />
        <Stat label="Questions" value={report.items} />
        <Stat label="Quiz-ready" value={report.quiz_ready} accent />
        <Stat label="Need review" value={report.needs_review} warning={report.needs_review > 0} />
      </SimpleGrid>

      {report.warnings.length > 0 ? (
        <Alert.Root status="warning" size="sm">
          <Alert.Indicator>
            <LuTriangleAlert size={15} />
          </Alert.Indicator>
          <Alert.Content>
            <Alert.Title>Worth checking</Alert.Title>
            <Alert.Description>
              <Stack gap="1">
                {report.warnings.map((warning) => (
                  <Text key={warning} fontSize="sm">
                    {warning}
                  </Text>
                ))}
              </Stack>
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      ) : null}

      <SimpleGrid columns={{ base: 1, md: 2 }} gap="5">
        <Stack gap="2">
          <Text fontSize="sm" fontWeight="medium">
            Field mapping
          </Text>
          <Stack gap="1.5">
            {Object.entries(report.plans).map(([name, plan]) => (
              <Flex key={name} justify="space-between" gap="3" fontSize="sm">
                <Text color="fg.muted" truncate>
                  {name}
                </Text>
                <Text fontSize="xs" color="fg.subtle" textAlign="right">
                  {[
                    plan.front ? `front: ${plan.front}` : null,
                    plan.reading ? `reading: ${plan.reading}` : null,
                    plan.combined ? `combined: ${plan.combined}` : null,
                    plan.meaning ? `meaning: ${plan.meaning}` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </Text>
              </Flex>
            ))}
          </Stack>
        </Stack>

        <Stack gap="2">
          <Text fontSize="sm" fontWeight="medium">
            Skipped
          </Text>
          {skippedEntries.length === 0 ? (
            <Flex align="center" gap="2" fontSize="sm" color="fg.muted">
              <LuCircleCheck size={14} />
              Nothing was skipped
            </Flex>
          ) : (
            <Stack gap="1.5">
              {skippedEntries.map(([reason, count]) => (
                <Flex key={reason} justify="space-between" gap="3" fontSize="sm">
                  <Flex align="center" gap="2" color="fg.muted">
                    <LuCircleSlash size={13} />
                    {SKIP_REASONS[reason] ?? reason.replaceAll("_", " ")}
                  </Flex>
                  <Text fontWeight="medium">{count}</Text>
                </Flex>
              ))}
              <Text fontSize="xs" color="fg.subtle">
                {skippedTotal} of {report.total_notes} notes skipped
              </Text>
            </Stack>
          )}
        </Stack>
      </SimpleGrid>

      {report.ambiguous.length > 0 ? (
        <Box borderWidth="1px" borderColor="border.muted" rounded="md" overflow="hidden">
          <Flex px="4" py="2.5" bg="bg.subtle" justify="space-between" align="center">
            <Text fontSize="sm" fontWeight="medium">
              Multiple valid readings
            </Text>
            <Badge variant="subtle" colorPalette="orange" rounded="full">
              {report.ambiguous.length}
            </Badge>
          </Flex>
          <Table.ScrollArea maxH="56">
            <Table.Root size="sm" variant="line">
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>Prompt</Table.ColumnHeader>
                  <Table.ColumnHeader>Readings</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {report.ambiguous.map((entry) => (
                  <Table.Row key={entry.front}>
                    <Table.Cell fontWeight="medium">{entry.front}</Table.Cell>
                    <Table.Cell color="fg.muted">{entry.readings.join(" · ")}</Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Root>
          </Table.ScrollArea>
        </Box>
      ) : null}
    </Stack>
  )
}

function Stat({
  label,
  value,
  accent,
  warning,
}: {
  label: string
  value: number
  accent?: boolean
  warning?: boolean
}) {
  return (
    <Stack gap="0.5">
      <Text fontSize="xs" color="fg.subtle">
        {label}
      </Text>
      <Text
        fontSize="xl"
        fontWeight="semibold"
        color={warning ? "fg.warning" : accent ? "fg.success" : "fg"}
      >
        {value}
      </Text>
    </Stack>
  )
}

export type { React }
