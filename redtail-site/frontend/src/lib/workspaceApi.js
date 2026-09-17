export async function workspacePost(endpoint, credentials, extra = {}, signal = undefined) {
  const response = await fetch(`/api/lore/${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...credentials, ...extra }), signal });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'This step could not finish. Please retry.');
  return data;
}
