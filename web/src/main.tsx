import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import { App } from "@/App"
import { AuthProvider } from "@/auth/AuthProvider"
import { Provider } from "@/components/ui/provider"
import { Toaster } from "@/components/ui/toaster"

const container = document.getElementById("root")

if (!container) {
  throw new Error("Root element #root was not found in index.html")
}

createRoot(container).render(
  <StrictMode>
    <Provider>
      <BrowserRouter>
        <AuthProvider>
          <App />
          <Toaster />
        </AuthProvider>
      </BrowserRouter>
    </Provider>
  </StrictMode>,
)
