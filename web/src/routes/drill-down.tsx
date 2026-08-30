/**
 * web/src/routes/drill-down.tsx — Phase 7b hierarchical drill-down route.
 *
 * Registered at /drill-down. Reads:
 *   - Phase 3 extracted_syllabi (via firestoreQueries.subscribePerTopicAssets)
 *   - Phase 4 topic_equivalent_edges (passed as props or fetched inline)
 *
 * The route composes the DrillDownPanel component with the react-router
 * session + subnation context. State management is local to the panel.
 */

import { useState } from "react";
import DrillDownPanel, {
  type DrillDownTopicEdge,
} from "../components/drill_down/DrillDownPanel";
import { useSession } from "../components/session/SessionContext";

export default function DrillDownRoute(): React.ReactNode {
  const { subnation } = useSession();
  const [markdownPath, setMarkdownPath] = useState<string | undefined>();

  // The Phase 4 equivalency graph isn't yet wired through Firestore;
  // when Phase 8 lands, this will subscribe to the topic_equivalent_edges
  // collection. For now we pass an empty list — the panel still shows
  // the 3-level drill + the markdown preview.
  const edges: DrillDownTopicEdge[] = [];

  return (
    <DrillDownPanel
      initialSubnation={subnation.code}
      edges={edges}
      markdownPath={markdownPath}
      onSelectMarkdown={setMarkdownPath}
    />
  );
}