const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api';

function csrfToken() {
  const token = document.cookie.split('; ').find((cookie) => cookie.startsWith('csrftoken='));
  return token ? decodeURIComponent(token.split('=').slice(1).join('=')) : '';
}

export type HelpRequestResponse = {
  id: number;
  status: string;
  message: string;
  intent: string;
  grounded: boolean;
  attachments: string[];
  createdAt: string;
};

export async function submitHelpRequest(message: string, files: File[]) {
  const form = new FormData();
  form.set('message', message);
  files.forEach((file) => form.append('files', file));
  const response = await fetch(`${API_BASE_URL}/support/requests`, { method: 'POST', body: form, credentials: 'include', headers: { 'X-CSRFToken': csrfToken() } });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(payload.detail ?? `Help request failed: ${response.status}`);
  }
  return response.json() as Promise<HelpRequestResponse>;
}
