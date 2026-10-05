import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const routesPath = path.join(root, "src", "routes.ts");
const layoutPath = path.join(root, "src", "components", "Layout.tsx");
const appPath = path.join(root, "src", "App.tsx");

const source = fs.readFileSync(routesPath, "utf8");
const pattern = /\{ id: "([^"]+)", path: "([^"]+)"(?:, aliases: \[([^\]]*)\])?.*?navigation: (true|false), uat: (true|false) \}/g;
const routes = [...source.matchAll(pattern)].map((match) => ({
  id: match[1],
  path: match[2],
  aliases: match[3] ? [...match[3].matchAll(/"([^"]+)"/g)].map((item) => item[1]) : [],
  navigation: match[4] === "true",
  uat: match[5] === "true",
}));

function fail(code, detail = "") {
  console.error(`${code}${detail ? ": " + detail : ""}`);
  process.exit(1);
}

if (routes.length !== 15) fail("ROUTE_REGISTRY_COUNT_MISMATCH", String(routes.length));
if (routes.filter((route) => route.uat).length !== 15) fail("UAT_ROUTE_COUNT_MISMATCH");
if (new Set(routes.map((route) => route.id)).size !== routes.length) fail("DUPLICATE_ROUTE_ID");
if (new Set(routes.map((route) => route.path)).size !== routes.length) fail("DUPLICATE_ROUTE_PATH");
if (!routes.some((route) => route.path === "/agent-console/initial-operation")) fail("INITIAL_OPERATION_ROUTE_MISSING");
if (routes.some((route) => route.path.includes("methodology"))) fail("NON_CANONICAL_METHODOLOGY_ROUTE_PRESENT");

const home = routes.find((route) => route.id === "home");
if (!home || !home.aliases.includes("/agent-console/index.html")) fail("INDEX_ALIAS_MISSING");

const layout = fs.readFileSync(layoutPath, "utf8");
const app = fs.readFileSync(appPath, "utf8");
if (!layout.includes("NAVIGATION_ROUTES")) fail("LAYOUT_NOT_BOUND_TO_ROUTE_REGISTRY");
if (!layout.includes("resolveAgentRoute")) fail("LAYOUT_ROUTE_IDENTITY_NOT_REGISTRY_BOUND");
if (!app.includes("resolveAgentRoute")) fail("APP_ROUTER_NOT_REGISTRY_BOUND");
if (app.includes('path === "/agent-console')) fail("LEGACY_LITERAL_ROUTER_CONDITION_PRESENT");

console.log(JSON.stringify({
  status: "PASS",
  canonical_routes: routes.length,
  uat_routes: routes.filter((route) => route.uat).length,
  navigation_routes: routes.filter((route) => route.navigation).length,
  initial_operation: true,
  methodology_registered: false,
  router_registry_bound: true,
  navigation_registry_bound: true,
}));
