const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail || data);
    throw new Error(message || `Request failed (${response.status})`);
  }
  return data;
}

export const api = {
  health: () => request("/health"),
  patients: () => request("/patients"),
  patient: (id) => request(`/patients/${encodeURIComponent(id)}`),
  bundle: (id) => request(`/patients/${encodeURIComponent(id)}/bundle`),
  summary: (id) => request(`/patients/${encodeURIComponent(id)}/summarize`, { method: "POST" }),
  validation: (id) => request(`/validation/${encodeURIComponent(id)}`),
  index: () => request("/index", { method: "POST" }),
  search: (payload) => request("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }),
  ingest: (files) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request("/ingest", { method: "POST", body: form });
  }
};
