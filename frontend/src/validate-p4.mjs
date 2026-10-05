import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (rel) => fs.readFileSync(path.join(root, rel), "utf8");
const fail = (code, detail = "") => {
  console.error(`P4_CONTRACT_FAIL:${code}${detail ? ":" + detail : ""}`);
  process.exit(1);
};

const routes = read("src/routes.ts");
const app = read("src/App.tsx");
const layout = read("src/components/Layout.tsx");
const design = read("src/design-system.css");

const definitions = [...routes.matchAll(/\{ id: "([^"]+)", path: "([^"]+)".*?uat: (true|false) \}/g)]
  .map((match) => ({ id: match[1], path: match[2], uat: match[3] === "true" }));
const canonical = definitions.filter((item) => item.uat);

if (canonical.length !== 15) fail("CANONICAL_ROUTE_COUNT", String(canonical.length));
if (new Set(canonical.map((item) => item.id)).size !== canonical.length) fail("DUPLICATE_ROUTE_ID");
if (new Set(canonical.map((item) => item.path)).size !== canonical.length) fail("DUPLICATE_ROUTE_PATH");
if (!canonical.some((item) => item.path === "/agent-console/initial-operation")) fail("INITIAL_OPERATION_MISSING");
if (canonical.some((item) => item.path === "/agent-console/methodology")) fail("METHODOLOGY_MUST_NOT_BE_CANONICAL");

if (!app.includes("resolveAgentRoute(location.pathname)")) fail("APP_NOT_USING_ROUTE_REGISTRY");
if (/path\s*===\s*"\/agent-console/.test(app)) fail("DIRECT_ROUTE_DISPATCH_REINTRODUCED");
if (!layout.includes("NAVIGATION_ROUTES")) fail("LAYOUT_NOT_USING_ROUTE_REGISTRY");
if (layout.includes("export const navigation")) fail("DUPLICATE_NAVIGATION_REGISTRY_REINTRODUCED");
if (!layout.includes('className="skip-link"')) fail("SKIP_LINK_MISSING");
if (!layout.includes('id="main-content"')) fail("MAIN_TARGET_MISSING");
if (!layout.includes("aria-current")) fail("ARIA_CURRENT_MISSING");
if (!design.includes("@media (prefers-reduced-motion: reduce)")) fail("REDUCED_MOTION_GATE_MISSING");

const appLines = app.split(/\r?\n/).length;
if (appLines >= 120) fail("APP_ROUTER_NOT_THIN", String(appLines));

const semanticTokens = new Set([...design.matchAll(/--pw-[a-z0-9-]+\s*:/g)].map((m) => m[0]));
if (semanticTokens.size < 30) fail("SEMANTIC_TOKEN_LAYER_TOO_SMALL", String(semanticTokens.size));

console.log(JSON.stringify({
  status: "PASS",
  canonicalRoutes: canonical.length,
  appLines,
  semanticTokens: semanticTokens.size,
  initialOperation: true,
  methodologyCanonical: false,
  skipLink: true,
  reducedMotion: true
}));
