const BASE_URL = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  searchHcps: (q) => request(`/hcps?q=${encodeURIComponent(q ?? "")}`),
  searchMaterials: (q, kind) => request(`/materials?kind=${kind}&q=${encodeURIComponent(q ?? "")}`),
  createInteraction: (payload) =>
    request("/interactions", { method: "POST", body: JSON.stringify(payload) }),
  updateInteraction: (id, payload) =>
    request(`/interactions/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listInteractions: (hcpId) => request(`/interactions?hcp_id=${hcpId}`),
  sendChatMessage: (payload) => request("/chat", { method: "POST", body: JSON.stringify(payload) }),
};
