// Service worker for the dashboard installed as a phone app: shows "ready to post" pushes and
// opens the posting queue when one is tapped. No offline cache: the dashboard needs the server.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  const d = e.data ? e.data.json() : {};
  e.waitUntil(self.registration.showNotification(d.title || "museai", {
    body: d.body || "",
    icon: "/dashboard/static/icon-192.png",
    badge: "/dashboard/static/icon-192.png",
    data: { url: d.url || "/dashboard#post" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL(e.notification.data?.url || "/dashboard#post", self.location.origin).href;
  e.waitUntil((async () => {
    for (const c of await self.clients.matchAll({ type: "window", includeUncontrolled: true })) {
      if (c.url.startsWith(self.location.origin + "/dashboard")) {
        await c.navigate(url).catch(() => {});
        return c.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});
