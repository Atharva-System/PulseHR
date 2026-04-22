import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./index.css";
import App from "./App.tsx";

// Force light mode at React level
document.documentElement.style.setProperty(
  "color-scheme",
  "light",
  "important",
);
document.documentElement.style.setProperty(
  "background-color",
  "#f8fafc",
  "important",
);
document.documentElement.style.setProperty("color", "#0f172a", "important");

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: true, // silently revalidate when user returns to tab
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
