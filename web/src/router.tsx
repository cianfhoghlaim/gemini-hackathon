/**
 * Vite + react-router-dom 7 route tree.
 *
 * Replaces the prior TanStack Start file-route system (createFileRoute +
 * routeTree.gen.ts). Routes are explicitly registered so the SPA shell
 * (`__root.tsx` rendering inside `<Outlet />`) mounts the right page
 * per URL.
 *
 * The API routes (`/api/themes`, `/api/duckdb`) are NOT registered here —
 * they're handled by a Vite dev-server plugin in `vite.config.ts` that
 * delegates to the Firebase Cloud Functions in `functions/src/`. In
 * production, the Cloud Run + Cloud Functions deployment is the source
 * of truth (per the comment in `web/src/routes/api/themes.ts`).
 */

import { createBrowserRouter } from "react-router-dom";
import App from "./routes/__root";

import IndexPage from "./routes/index";
import SubjectsPage from "./routes/subjects";
import SubjectDetailPage from "./routes/subjects.$slug";
import SafeguardingPage from "./routes/safeguarding";
import FindResourcesPage from "./routes/find-resources";
import AgentChatPage from "./routes/agents";
import DrillDownRoute from "./routes/drill-down";
import ArchipelagoPage from "./routes/archipelago";
import ComparePage from "./routes/compare";
import EquivalencyPage from "./routes/equivalency";
import LearningGraphsPage from "./routes/learning-graphs";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <IndexPage /> },
      { path: "subjects", element: <SubjectsPage /> },
      { path: "subjects/:slug", element: <SubjectDetailPage /> },
      { path: "safeguarding", element: <SafeguardingPage /> },
      { path: "find-resources", element: <FindResourcesPage /> },
      { path: "agents", element: <AgentChatPage /> },
      { path: "drill-down", element: <DrillDownRoute /> },
      { path: "archipelago", element: <ArchipelagoPage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "equivalency", element: <EquivalencyPage /> },
      { path: "learning-graphs", element: <LearningGraphsPage /> },
    ],
  },
]);