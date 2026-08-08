#!/usr/bin/env node
/*
 * PalWakf Local Agents — Read-Only Browser UAT via Edge DevTools Protocol.
 * The script never sends application writes. It records browser-originated
 * requests and fails if the SPA emits a non-GET request, authorization/cookie
 * header from React fetches, or a console error.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

function parseArgs(argv) {
  const values = {};
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (!key.startsWith('--')) continue;
    const name = key.slice(2);
    const next = argv[i + 1];
    if (next && !next.startsWith('--')) { values[name] = next; i += 1; }
    else values[name] = true;
  }
  return values;
}
const args = parseArgs(process.argv.slice(2));
const baseUrl = String(args['base-url'] ?? 'http://127.0.0.1:8787').replace(/\/$/, '');
const outputDirectory = path.resolve(String(args.output ?? './BROWSER_UAT'));
const edgePath = String(args['edge-path'] ?? process.env.EDGE_PATH ?? 'msedge.exe');
const debugPort = Number(args['debug-port'] ?? 9228);
const timeoutMs = Number(args['timeout-ms'] ?? 45000);
const keepBrowser = args['keep-browser'] === true;

if (typeof globalThis.WebSocket !== 'function') {
  throw new Error('NODE_22_OR_LATER_REQUIRED_FOR_NATIVE_WEBSOCKET');
}

await fs.mkdir(outputDirectory, { recursive: true });
const browserProfile = path.join(outputDirectory, 'EDGE_PROFILE');
await fs.mkdir(browserProfile, { recursive: true });

function httpJson(url, method = 'GET') {
  return new Promise((resolve, reject) => {
    const request = http.request(url, { method }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf8');
        if (response.statusCode < 200 || response.statusCode >= 300) {
          reject(new Error(`HTTP_${response.statusCode}:${body.slice(0, 500)}`)); return;
        }
        try { resolve(JSON.parse(body)); } catch (error) { reject(error); }
      });
    });
    request.on('error', reject);
    request.end();
  });
}

async function waitForVersion() {
  const url = `http://127.0.0.1:${debugPort}/json/version`;
  const started = Date.now();
  let lastError = null;
  while (Date.now() - started < timeoutMs) {
    try { return await httpJson(url); } catch (error) { lastError = error; await sleep(250); }
  }
  throw new Error(`EDGE_DEVTOOLS_NOT_READY:${lastError?.message ?? 'UNKNOWN'}`);
}

class Cdp {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.pending = new Map();
    this.listeners = new Set();
    this.nextId = 1;
  }
  async connect() {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('CDP_CONNECT_TIMEOUT')), timeoutMs);
      this.ws.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
      this.ws.addEventListener('error', (event) => { clearTimeout(timer); reject(new Error(`CDP_CONNECT_ERROR:${event?.message ?? 'UNKNOWN'}`)); }, { once: true });
      this.ws.addEventListener('message', (event) => this.#message(event));
      this.ws.addEventListener('close', () => {
        for (const { reject } of this.pending.values()) reject(new Error('CDP_CONNECTION_CLOSED'));
        this.pending.clear();
      });
    });
  }
  #message(event) {
    let payload;
    try { payload = JSON.parse(String(event.data)); } catch { return; }
    if (payload.id && this.pending.has(payload.id)) {
      const { resolve, reject } = this.pending.get(payload.id);
      this.pending.delete(payload.id);
      if (payload.error) reject(new Error(`CDP_${payload.error.code}:${payload.error.message}`));
      else resolve(payload.result ?? {});
      return;
    }
    for (const listener of this.listeners) listener(payload);
  }
  send(method, params = {}, sessionId = undefined) {
    const id = this.nextId++;
    const request = { id, method, params };
    if (sessionId) request.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        if (this.pending.has(id)) { this.pending.delete(id); reject(new Error(`CDP_TIMEOUT:${method}`)); }
      }, timeoutMs);
      this.pending.set(id, {
        resolve: (result) => { clearTimeout(timer); resolve(result); },
        reject: (error) => { clearTimeout(timer); reject(error); },
      });
      this.ws.send(JSON.stringify(request));
    });
  }
  onEvent(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }
  close() { try { this.ws.close(); } catch {} }
}

function safeFileName(value) { return value.replace(/[^a-zA-Z0-9_-]+/g, '_'); }
function normalizedHeaderMap(headers = {}) {
  return Object.fromEntries(Object.entries(headers).map(([key, value]) => [String(key).toLowerCase(), String(value)]));
}

const edgeArgs = [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  `--remote-debugging-port=${debugPort}`, `--user-data-dir=${browserProfile}`, 'about:blank',
];
const edge = spawn(edgePath, edgeArgs, { windowsHide: true, stdio: 'ignore' });
let report;
try {
  const version = await waitForVersion();
  const cdp = new Cdp(version.webSocketDebuggerUrl);
  await cdp.connect();
  const routes = [
    { name: 'START_DESKTOP', path: '/agent-console/', viewport: { width: 1440, height: 1024, mobile: false } },
    { name: 'START_MOBILE', path: '/agent-console/', viewport: { width: 390, height: 844, mobile: true } },
    { name: 'WORKSPACES_DESKTOP', path: '/agent-console/workspaces', viewport: { width: 1440, height: 1024, mobile: false } },
    { name: 'TASKS_DESKTOP', path: '/agent-console/tasks', viewport: { width: 1440, height: 1024, mobile: false } },
    { name: 'DIAGNOSTICS_DESKTOP', path: '/agent-console/diagnostics', viewport: { width: 1440, height: 1024, mobile: false } },
  ];
  const pages = [];
  const allRequests = [];
  const consoleEntries = [];

  for (const route of routes) {
    const created = await cdp.send('Target.createTarget', { url: 'about:blank', width: route.viewport.width, height: route.viewport.height, newWindow: false, background: true });
    const attached = await cdp.send('Target.attachToTarget', { targetId: created.targetId, flatten: true });
    const sessionId = attached.sessionId;
    const network = [];
    const routeConsole = [];
    let loaded = false;
    const unregister = cdp.onEvent((event) => {
      if (event.sessionId !== sessionId) return;
      if (event.method === 'Network.requestWillBeSent') {
        const request = event.params.request;
        network.push({
          url: request.url,
          method: request.method,
          headers: normalizedHeaderMap(request.headers),
          type: event.params.type ?? 'UNKNOWN',
          initiator: event.params.initiator?.type ?? 'UNKNOWN',
        });
      }
      if (event.method === 'Runtime.consoleAPICalled') {
        const entry = { kind: event.params.type, args: event.params.args?.map((arg) => arg.value ?? arg.description ?? arg.type) ?? [] };
        routeConsole.push(entry); consoleEntries.push({ route: route.name, ...entry });
      }
      if (event.method === 'Log.entryAdded') {
        const entry = { kind: event.params.entry.level, text: event.params.entry.text ?? '' };
        routeConsole.push(entry); consoleEntries.push({ route: route.name, ...entry });
      }
      if (event.method === 'Page.loadEventFired') loaded = true;
    });
    try {
      await cdp.send('Page.enable', {}, sessionId);
      await cdp.send('Network.enable', {}, sessionId);
      await cdp.send('Runtime.enable', {}, sessionId);
      await cdp.send('Log.enable', {}, sessionId);
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: route.viewport.width, height: route.viewport.height, deviceScaleFactor: 1,
        mobile: route.viewport.mobile, screenWidth: route.viewport.width, screenHeight: route.viewport.height,
      }, sessionId);
      await cdp.send('Page.navigate', { url: `${baseUrl}${route.path}` }, sessionId);
      const started = Date.now();
      while (!loaded && Date.now() - started < timeoutMs) await sleep(100);
      if (!loaded) throw new Error(`PAGE_LOAD_TIMEOUT:${route.name}`);
      await sleep(1100);
      const inspected = await cdp.send('Runtime.evaluate', {
        expression: `(() => {
          const shell = document.querySelector('.app-shell');
          const sidebar = document.querySelector('.sidebar');
          const menu = document.querySelector('.menu-button');
          const backdrop = document.querySelector('.drawer-backdrop');
          const preOrLongCode = [...document.querySelectorAll('pre, code')].some((node) => (node.textContent || '').trim().length > 120);
          const bodyText = document.body?.innerText || '';
          const computed = shell ? getComputedStyle(shell) : null;
          return {
            title: document.title,
            appShellPresent: Boolean(shell),
            direction: computed?.direction || '',
            sidebarClass: sidebar?.className || '',
            sidebarDisplay: sidebar ? getComputedStyle(sidebar).display : '',
            menuDisplay: menu ? getComputedStyle(menu).display : '',
            menuPresent: Boolean(menu),
            backdropPresent: Boolean(backdrop),
            primaryNavPresent: Boolean(document.querySelector('.primary-nav')),
            rawJsonPrimarySurface: preOrLongCode,
            blockedTextPresent: bodyText.includes('لا توجد أوامر تشغيل') || bodyText.includes('محجوب') || bodyText.includes('مقفل'),
            readOnlyTextPresent: bodyText.includes('عرض محكوم') || bodyText.includes('قراءة محكومة'),
            bodyLength: bodyText.length,
          };
        })()`, returnByValue: true,
      }, sessionId);
      let mobileDrawer = null;
      if (route.name === 'START_MOBILE') {
        await cdp.send('Runtime.evaluate', { expression: `document.querySelector('.menu-button')?.click()`, awaitPromise: false }, sessionId);
        await sleep(350);
        mobileDrawer = await cdp.send('Runtime.evaluate', {
          expression: `(() => ({
            sidebarOpen: document.querySelector('.sidebar')?.classList.contains('sidebar-open') || false,
            backdropPresent: Boolean(document.querySelector('.drawer-backdrop')),
            navStacking: getComputedStyle(document.querySelector('.sidebar') || document.body).position !== 'fixed'
          }))()`, returnByValue: true,
        }, sessionId);
      }
      const screenshot = await cdp.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, sessionId);
      await fs.writeFile(path.join(outputDirectory, `${route.name}.png`), Buffer.from(screenshot.data, 'base64'));
      const dom = await cdp.send('Runtime.evaluate', { expression: 'document.documentElement.outerHTML', returnByValue: true }, sessionId);
      await fs.writeFile(path.join(outputDirectory, `${route.name}.html`), String(dom.result.value ?? ''), 'utf8');
      pages.push({ route: route.name, url: `${baseUrl}${route.path}`, inspection: inspected.result.value, mobileDrawer: mobileDrawer?.result?.value ?? null, requests: network, console: routeConsole });
      allRequests.push(...network.map((entry) => ({ route: route.name, ...entry })));
    } finally {
      unregister();
      try { await cdp.send('Target.closeTarget', { targetId: created.targetId }); } catch {}
    }
  }
  cdp.close();
  const httpMethods = [...new Set(allRequests.map((request) => request.method))].sort();
  const nonGet = allRequests.filter((request) => request.method !== 'GET');
  const appFetches = allRequests.filter((request) => request.type === 'Fetch' || request.type === 'XHR');
  const authHeaders = appFetches.filter((request) => request.headers.authorization || request.headers.cookie || request.headers['proxy-authorization']);
  const consoleErrors = consoleEntries.filter((entry) => ['error', 'assert'].includes(String(entry.kind).toLowerCase()));
  const pageByName = Object.fromEntries(pages.map((page) => [page.route, page]));
  const desktop = pageByName.START_DESKTOP?.inspection ?? {};
  const mobile = pageByName.START_MOBILE?.inspection ?? {};
  const mobileDrawer = pageByName.START_MOBILE?.mobileDrawer ?? {};
  const routeShellFailures = pages.filter((page) => !page.inspection?.appShellPresent || !page.inspection?.primaryNavPresent || page.inspection?.direction !== 'rtl' || !page.inspection?.readOnlyTextPresent || page.inspection?.rawJsonPrimarySurface);
  const diagnostics = pageByName.DIAGNOSTICS_DESKTOP?.inspection ?? {};
  const acceptance = {
    RTL_RENDER: routeShellFailures.length === 0 ? 'PASS' : 'FAIL',
    DESKTOP_NAVIGATION: desktop.sidebarDisplay !== 'none' && desktop.menuDisplay === 'none' ? 'PASS' : 'FAIL',
    MOBILE_DRAWER: mobile.menuPresent && mobile.menuDisplay !== 'none' && mobileDrawer.sidebarOpen && mobileDrawer.backdropPresent ? 'PASS' : 'FAIL',
    NO_MOBILE_NAV_STACKING: mobileDrawer.navStacking === false ? 'PASS' : 'FAIL',
    NO_RAW_JSON_PRIMARY_SURFACE: routeShellFailures.length === 0 ? 'PASS' : 'FAIL',
    GET_ONLY_NETWORK: nonGet.length === 0 ? 'PASS' : 'FAIL',
    CREDENTIALS_OMIT_OBSERVED: authHeaders.length === 0 ? 'PASS' : 'FAIL',
    NO_REACT_WRITE: nonGet.length === 0 ? 'PASS' : 'FAIL',
    NO_MODEL_OR_PILOT_EXECUTION: pages.every((page) => !page.requests.some((request) => /model|pilot/i.test(request.url) && request.method !== 'GET')) ? 'PASS' : 'FAIL',
    CONSOLE_ERRORS: consoleErrors.length === 0 ? 'PASS' : 'FAIL',
    DIAGNOSTICS_RENDER: diagnostics.appShellPresent && diagnostics.readOnlyTextPresent ? 'PASS' : 'FAIL',
  };
  const failures = Object.entries(acceptance).filter(([, value]) => value !== 'PASS').map(([key]) => key);
  report = {
    authorization: 'AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY',
    execution_scope: 'ISOLATED_WORKTREE_ONLY',
    base_url: baseUrl,
    browser: 'Microsoft Edge via CDP',
    application_write_by_uat_runner: 'NONE',
    request_methods_observed: httpMethods,
    requests: allRequests,
    pages,
    console_entries: consoleEntries,
    acceptance,
    result: failures.length === 0 ? 'WINDOWS_RUNTIME_UAT_PASS' : 'WINDOWS_RUNTIME_UAT_FAIL',
    failures,
  };
  await fs.writeFile(path.join(outputDirectory, 'BROWSER_UAT_REPORT.json'), JSON.stringify(report, null, 2), 'utf8');
  await fs.writeFile(path.join(outputDirectory, 'NETWORK_SUMMARY.json'), JSON.stringify({ requests: allRequests, non_get: nonGet, application_fetches_with_auth_or_cookie: authHeaders }, null, 2), 'utf8');
  await fs.writeFile(path.join(outputDirectory, 'CONSOLE.json'), JSON.stringify(consoleEntries, null, 2), 'utf8');
  if (report.result !== 'WINDOWS_RUNTIME_UAT_PASS') process.exitCode = 2;
} catch (error) {
  report = {
    authorization: 'AUTHORIZE_LOCAL_AGENTS_PRODUCT_START_SCREEN_AND_OPERATIONAL_CONSOLE_READ_ONLY_WINDOWS_RUNTIME_UAT_V1_ISOLATED_WORKTREE_ONLY',
    execution_scope: 'ISOLATED_WORKTREE_ONLY',
    result: 'WINDOWS_RUNTIME_UAT_HARNESS_ERROR',
    error: error instanceof Error ? error.message : String(error),
  };
  await fs.writeFile(path.join(outputDirectory, 'BROWSER_UAT_REPORT.json'), JSON.stringify(report, null, 2), 'utf8');
  process.exitCode = 3;
} finally {
  if (!keepBrowser) {
    try { edge.kill(); } catch {}
  }
}
