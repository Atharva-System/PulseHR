import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
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

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
