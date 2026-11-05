import { Flex, Text } from "@chakra-ui/react"
import { LuTriangleAlert } from "react-icons/lu"

/**
 * Inline, form-level error message. Used when a backend failure does not map to
 * a single input (for example "Incorrect username or password").
 */
export function FormError({ children }: { children: React.ReactNode }) {
  return (
    <Flex
      align="center"
      gap="2.5"
      bg="bg.error"
      borderWidth="1px"
      borderColor="border.error"
      rounded="md"
      px="3"
      py="2.5"
      color="fg.error"
    >
      <LuTriangleAlert size={15} />
      <Text fontSize="sm">{children}</Text>
    </Flex>
  )
}
