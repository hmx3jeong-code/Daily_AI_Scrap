const CACHE_VERSION = "2026-03-19-1";
const STATIC_CACHE = `daily-ai-brief-static-${CACHE_VERSION}`;
const DATA_CACHE = `daily-ai-brief-data-${CACHE_VERSION}`;

const APP_SHELL = [
  "./",
  "./index.html",
  "./offline.html",
  "./manifest.webmanifest",
  "./data/latest.json",
  "./data/index.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-512-maskable.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(async (cache) => {
      await Promise.all(
        APP_SHELL.map(async (asset) => {
          try {
            await cache.add(asset);
          } catch {
            // Ignore per-file failures and continue installation.
          }
        })
      );
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key.startsWith("daily-ai-brief-") && key !== STATIC_CACHE && key !== DATA_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

function isSameOrigin(requestUrl) {
  return new URL(requestUrl).origin === self.location.origin;
}

function isDataRequest(requestUrl) {
  const url = new URL(requestUrl);
  return url.pathname.endsWith(".json") && url.pathname.includes("/data/");
}

function toDataCacheKey(request) {
  const url = new URL(request.url);
  url.search = "";
  return new Request(url.toString(), { method: "GET" });
}

async function networkFirstData(request) {
  const cache = await caches.open(DATA_CACHE);
  const cacheKey = toDataCacheKey(request);
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(cacheKey, response.clone());
    }
    return response;
  } catch {
    const cached = (await cache.match(cacheKey)) || (await caches.match(cacheKey));
    if (cached) return cached;
    return new Response("{}", { headers: { "Content-Type": "application/json" } });
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response && response.ok && isSameOrigin(request.url)) {
    const cache = await caches.open(STATIC_CACHE);
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    if (response && response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put("./index.html", response.clone());
    }
    return response;
  } catch {
    return (await caches.match("./index.html")) || (await caches.match("./offline.html"));
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  if (!isSameOrigin(request.url)) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (isDataRequest(request.url)) {
    event.respondWith(networkFirstData(request));
    return;
  }

  event.respondWith(
    cacheFirst(request).catch(async () => (await caches.match("./offline.html")) || Response.error())
  );
});
