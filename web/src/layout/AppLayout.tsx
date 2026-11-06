import {
  Avatar,
  Box,
  Button,
  Flex,
  Link,
  Menu,
  Portal,
  Separator,
  Stack,
  Text,
} from "@chakra-ui/react"
import { LuChevronDown, LuLogOut, LuSettings, LuUser } from "react-icons/lu"
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { BrandMark } from "@/components/BrandMark"
import { useAuth } from "@/auth/AuthProvider"

const navigation = [
  { label: "Overview", to: "/" },
  { label: "Decks", to: "/decks" },
  { label: "Settings", to: "/settings" },
]

/**
 * Persistent application frame: a slim top bar over a full-height canvas.
 * Navigation is intentionally text-only to keep the chrome minimal.
 */
export function AppLayout() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const displayName = user?.full_name?.trim() || user?.username || "Account"

  function handleLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <Flex minH="100dvh" direction="column" bg="bg">
      <Box
        as="header"
        position="sticky"
        top="0"
        zIndex="docked"
        borderBottomWidth="1px"
        borderColor="border.muted"
        bg="bg/80"
        backdropFilter="blur(12px)"
      >
        <Flex
          mx="auto"
          maxW="6xl"
          h="14"
          px={{ base: "4", md: "6" }}
          align="center"
          justify="space-between"
          gap="6"
        >
          <Flex align="center" gap={{ base: "5", md: "8" }}>
            <RouterLink to="/" aria-label="Crolo home">
              <BrandMark size="sm" />
            </RouterLink>

            <Flex as="nav" align="center" gap="1">
              {navigation.map((item) => {
                const isActive =
                  item.to === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.to)

                return (
                  <Link
                    key={item.to}
                    asChild
                    fontSize="sm"
                    px="2.5"
                    py="1.5"
                    rounded="md"
                    color={isActive ? "fg" : "fg.muted"}
                    bg={isActive ? "bg.muted" : "transparent"}
                    fontWeight={isActive ? "medium" : "normal"}
                    _hover={{ textDecoration: "none", color: "fg", bg: "bg.subtle" }}
                  >
                    <RouterLink to={item.to}>{item.label}</RouterLink>
                  </Link>
                )
              })}
            </Flex>
          </Flex>

          <Menu.Root positioning={{ placement: "bottom-end" }}>
            <Menu.Trigger asChild>
              <Button variant="ghost" colorPalette="gray" size="sm" px="1.5">
                <Avatar.Root size="2xs" colorPalette="brand">
                  <Avatar.Fallback name={displayName} />
                </Avatar.Root>
                <Text as="span" hideBelow="sm" maxW="32" truncate>
                  {user?.username ?? "Account"}
                </Text>
                <LuChevronDown />
              </Button>
            </Menu.Trigger>
            <Portal>
              <Menu.Positioner>
                <Menu.Content minW="52">
                  <Stack px="2" py="1.5" gap="0.5">
                    <Text fontSize="sm" fontWeight="medium" truncate>
                      {displayName}
                    </Text>
                    <Text fontSize="xs" color="fg.muted" truncate>
                      {user?.email ?? "No email on file"}
                    </Text>
                  </Stack>
                  <Separator borderColor="border.muted" />
                  <Menu.Item value="settings" asChild>
                    <RouterLink to="/settings">
                      <LuSettings />
                      <Menu.ItemText>Settings</Menu.ItemText>
                    </RouterLink>
                  </Menu.Item>
                  <Menu.Item value="account" asChild>
                    <RouterLink to="/">
                      <LuUser />
                      <Menu.ItemText>Overview</Menu.ItemText>
                    </RouterLink>
                  </Menu.Item>
                  <Separator borderColor="border.muted" />
                  <Menu.Item value="logout" onClick={handleLogout}>
                    <LuLogOut />
                    <Menu.ItemText>Sign out</Menu.ItemText>
                  </Menu.Item>
                </Menu.Content>
              </Menu.Positioner>
            </Portal>
          </Menu.Root>
        </Flex>
      </Box>

      <Box flex="1" mx="auto" w="full" maxW="6xl" px={{ base: "4", md: "6" }} py="10">
        <Outlet />
      </Box>

      <Box
        as="footer"
        borderTopWidth="1px"
        borderColor="border.muted"
        py="5"
        px={{ base: "4", md: "6" }}
      >
        <Flex mx="auto" maxW="6xl" justify="space-between" gap="4">
          <Text textStyle="xs" color="fg.subtle">
            Crolo
          </Text>
          <Text textStyle="xs" color="fg.subtle">
            Secured with OAuth2 bearer tokens
          </Text>
        </Flex>
      </Box>
    </Flex>
  )
}
