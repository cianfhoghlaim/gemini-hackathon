/**
 * SessionAgentContext — propagates the active session (subnation + role +
 * cycle + selected subjects + safeguarding source) into every CopilotKit
 * agent as a typed context payload.
 *
 * Uses `useAgentContext()` from `@copilotkit/react-core/v2` — a
 * module-level hook that registers a `{ description, value }` pair on
 * the agent. Mount this component inside `<CopilotKit>` (the provider)
 * so the context is available on every page, not just /agents.
 *
 * Each `useAgentContext()` call is keyed by `description`; multiple
 * components can each contribute their own context slot without
 * clobbering one another. The agent receives the merged context as
 * structured input on every turn.
 */

import { useEffect } from "react";
import { useAgentContext } from "@copilotkit/react-core/v2";
import { useSession } from "./SessionContext";

export function SessionAgentContext(): null {
  const { session, subnation, isDefault } = useSession();

  // Subnation identity (the strongest signal — drives the safeguarding
  // policy lookup + the per-source palette + the chat greeting).
  useAgentContext({
    description: "session.subnation",
    value: {
      code: subnation.code,
      name: subnation.name,
      flag: subnation.flag,
      awardingBody: subnation.awardingBody,
      awardingBodyShort: subnation.awardingBodyShort,
      isDefault,
    },
  });

  // Role + cycle (the role drives the home page's quick actions + the
  // agent's voice — student vs parent vs teacher).
  useAgentContext({
    description: "session.role",
    value: session
      ? {
          role: session.role,
          cycle: session.cycle,
          onboarded: session.onboarded,
          uid: session.uid,
          email: session.email,
        }
      : { role: "anonymous", cycle: "leaving_cycle", onboarded: false },
  });

  // Selected subjects (the user explicitly opted into these — drives
  // the chat suggestions + the resource discovery filter).
  useAgentContext({
    description: "session.subjects",
    value: session?.selectedSubjects ?? [],
  });

  // Safeguarding source key (the active jurisdiction's safeguarding
  // body — wired to the per-source palette + the safeguarding page).
  useAgentContext({
    description: "session.safeguarding",
    value: session?.safeguardingSourceKey ?? "gov.ie/education",
  });

  useEffect(() => {
    // No-op effect — the hooks above re-register on every render so the
    // agent always sees the latest values. The effect here keeps
    // `useEffect` imported for the comment's sake (eslint-plugin-react
    // may flag the unused import otherwise).
  }, [session]);

  return null;
}