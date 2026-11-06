import { expect, test, type Page } from "@playwright/test"
import path from "node:path"
import { fileURLToPath } from "node:url"

const here = path.dirname(fileURLToPath(import.meta.url))
const deckPath = path.resolve(here, "../../api/tests/fixtures/10月20日.apkg")

function uniqueUser() {
  return `e2e_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`
}

async function register(page: Page, fullName: string) {
  const username = uniqueUser()
  await page.goto("/register")
  await page.getByLabel("Full name").fill(fullName)
  await page.getByLabel("Username").fill(username)
  await page.getByLabel("Email").fill(`${username}@example.com`)
  await page.locator("#password").fill("secret123")
  await page.getByRole("button", { name: /create account/i }).click()
  await expect(page.getByRole("heading", { name: new RegExp(`hello, ${fullName}`, "i") })).toBeVisible()
}

async function importDeck(page: Page) {
  await page.goto("/decks")
  await expect(page.getByRole("heading", { name: "Quiz decks" })).toBeVisible()
  await page.locator('input[type="file"]').setInputFiles(deckPath)
  await expect(page.getByText(/import report/i)).toBeVisible({ timeout: 60_000 })
}

test("import → review → edit → publish → instant quiz → results", async ({ page }) => {
  await register(page, "E2E Tester")
  await importDeck(page)

  await expect(page.getByText("10月20日", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Review questions" }).click()
  await expect(page.getByRole("heading", { name: "10月20日", exact: true })).toBeVisible()
  await expect(page.getByText(/15 questions · 15 ready/)).toBeVisible()

  // Edit the translation of the first question, then save in one request.
  const firstRow = page.locator("tbody tr").first()
  await firstRow.getByRole("textbox").nth(2).fill("self-blame (edited)")
  await page.getByRole("button", { name: /save changes/i }).click()
  await expect(page.getByText("Changes saved")).toBeVisible()

  await page.getByRole("button", { name: "Publish deck" }).click()
  await expect(page.getByRole("button", { name: "Start quiz" })).toBeVisible()
  await page.getByRole("button", { name: "Start quiz" }).click()
  await page.getByRole("button", { name: "All", exact: true }).last().click()
  await page.getByRole("button", { name: "Start session" }).click()

  // Instant feedback: choose with the keyboard, verify feedback, then advance.
  const counter = page.getByText(/^\d+ \/ \d+$/)
  await expect(counter).toBeVisible()
  const total = Number((await counter.textContent())?.split("/")[1]?.trim() ?? "0")
  expect(total).toBeGreaterThan(0)

  for (let question = 0; question < total; question += 1) {
    await page.keyboard.press("1")
    await expect(page.getByText(/Correct|Not quite/)).toBeVisible()
    await page.keyboard.press("Enter")
  }

  await expect(page).toHaveURL(/\/sessions\/\d+\/results/, { timeout: 15_000 })
  await expect(
    page.getByRole("heading", { name: /nicely done|getting there|keep practising/i }),
  ).toBeVisible()
  await expect(page.getByText(/correct on this run/i)).toBeVisible()

  // The edited translation is visible in the results table.
  await expect(page.getByText("self-blame (edited)")).toBeVisible()
})

test("end-of-session mode hides correctness until results", async ({ page }) => {
  await register(page, "E2E Late")
  await importDeck(page)

  await page.getByRole("button", { name: "Review questions" }).click()
  await page.getByRole("button", { name: "Publish deck" }).click()
  await page.getByRole("button", { name: "Start quiz" }).click()

  await page.getByText("Answers at the end", { exact: true }).click()
  await expect(page.getByRole("radio", { name: "Answers at the end" })).toBeChecked()
  await page.getByRole("button", { name: "Start session" }).click()
  await expect(page.getByText(/^1 \/ \d+$/)).toBeVisible()

  await page.getByRole("button", { name: /^1 / }).click()
  // No correctness banner and no reading hint in this mode.
  await expect(page.getByText(/Correct|Not quite/)).toHaveCount(0)
  await expect(page.getByRole("button", { name: /^1 / })).toHaveAttribute("aria-pressed", "true")

  // The choice survives navigating away and back.
  await page.getByRole("button", { name: "Next" }).click()
  await page.getByRole("button", { name: "Back" }).click()
  await expect(page.getByRole("button", { name: /^1 / })).toHaveAttribute("aria-pressed", "true")
})

test("add a question by hand", async ({ page }) => {
  await register(page, "E2E Editor")
  await importDeck(page)
  await page.getByRole("button", { name: "Review questions" }).click()

  await page.getByRole("button", { name: "Add question" }).click()
  await page.getByPlaceholder("経済").fill("経済")
  await page.getByPlaceholder("けいざい").fill("けいざい")
  await page.getByPlaceholder("economy").fill("economy")
  await page.getByRole("dialog").getByRole("button", { name: "Add question" }).click()

  await expect(page.getByText(/16 questions/)).toBeVisible()
})

test("end-of-session mode reveals results only after finishing", async ({ page }) => {
  await register(page, "E2E Finish")
  await importDeck(page)

  await page.getByRole("button", { name: "Review questions" }).click()
  await page.getByRole("button", { name: "Publish deck" }).click()
  await page.getByRole("button", { name: "Start quiz" }).click()
  await page.getByText("Answers at the end", { exact: true }).click()
  await page.getByRole("button", { name: "10", exact: true }).click()
  await page.getByRole("button", { name: "Start session" }).click()

  const counter = page.getByText(/^\d+ \/ \d+$/)
  await expect(counter).toBeVisible()
  const total = Number((await counter.textContent())?.split("/")[1]?.trim() ?? "0")
  expect(total).toBeGreaterThan(0)

  for (let question = 0; question < total; question += 1) {
    await page.keyboard.press("1")
    if (question < total - 1) {
      await page.getByRole("button", { name: "Next" }).click()
    }
  }

  await page.getByRole("button", { name: /finish session/i }).click()
  await expect(page).toHaveURL(/\/sessions\/\d+\/results/, { timeout: 15_000 })
  await expect(
    page.getByRole("heading", { name: /nicely done|getting there|keep practising/i }),
  ).toBeVisible()
  await expect(page.getByText(/correct on this run/i)).toBeVisible()
})
