/**
 * Vite + react-router-dom 7 entry point.
 *
 * Migrated from TanStack Start (`getRouter()` + RouterProvider) to the
 * plain `createBrowserRouter` + `RouterProvider` pattern. The route
 * tree is in `src/router.tsx`.
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./router";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("No #root element");

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);