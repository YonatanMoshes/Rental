/**
 * Application entry point.
 * 
 * Renders the root React component into the DOM and enables StrictMode
 * for additional development-time checks.
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
