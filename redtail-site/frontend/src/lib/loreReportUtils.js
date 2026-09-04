export function escapeHtml(s) {
  return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function slug(s) {
  return String(s || "report").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "report";
}

export function downloadHtml(html, filename) {
  if (!html) return;
  const blob = new Blob([html], { type: "text/html" });
  downloadBlob(blob, filename);
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Fetches an authenticated endpoint and saves the response as a local file —
// used for admin export/backup buttons (e.g. the waitlist backup).
export async function downloadFromApi(url, filename) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Download failed (${r.status})`);
  const blob = await r.blob();
  downloadBlob(blob, filename);
}
