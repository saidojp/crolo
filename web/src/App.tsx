import { Navigate, Route, Routes } from "react-router-dom"

import { AppLayout } from "@/layout/AppLayout"
import { DashboardPage } from "@/pages/DashboardPage"
import { DeckDetailPage } from "@/pages/DeckDetailPage"
import { DecksPage } from "@/pages/DecksPage"
import { LoginPage } from "@/pages/LoginPage"
import { QuizPage } from "@/pages/QuizPage"
import { RegisterPage } from "@/pages/RegisterPage"
import { ResultsPage } from "@/pages/ResultsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { GuestRoute, ProtectedRoute } from "@/routes/RouteGuards"

export function App() {
  return (
    <Routes>
      <Route element={<GuestRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/decks" element={<DecksPage />} />
          <Route path="/decks/:deckId" element={<DeckDetailPage />} />
          <Route path="/decks/:deckId/quiz" element={<QuizPage />} />
          <Route path="/sessions/:sessionId/results" element={<ResultsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
