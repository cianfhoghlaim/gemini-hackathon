import { createRouter as createTanstackRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

export function getRouter() {
    const router = createTanstackRouter({
        routeTree,
        defaultPreload: "intent",
        defaultPreloadStaleTime: 0,
    });
    return router;
}
