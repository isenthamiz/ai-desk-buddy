import { Platform } from 'react-native';

export type BuddyState = 'SLEEPING' | 'IDLE' | 'LISTENING' | 'THINKING' |
  'SPEAKING' | 'TIMER' | 'ALERT' | 'OFFLINE' | 'ERROR';

export type ControlStatus = {
  backend: 'online';
  device: {
    id: string;
    type: 'SIMULATOR' | 'ESP32' | null;
    connected: boolean;
    state: BuddyState;
  };
  timer: { active: boolean; durationSeconds: number | null };
};

export type Reminder = {
  id: string;
  text: string;
  dueAt: string;
  status: 'PENDING';
};

const fallbackUrl = Platform.OS === 'web'
  ? 'http://127.0.0.1:8000'
  : 'http://127.0.0.1:8000';

export const apiBaseUrl = (
  process.env.EXPO_PUBLIC_BUDDY_API_URL || fallbackUrl
).replace(/\/$/, '');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // Keep the status-based fallback when the server did not return JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export const controlApi = {
  status: () => request<ControlStatus>('/api/control/status'),
  sendText: (text: string) => request<{ ok: true }>('/api/control/messages', {
    method: 'POST', body: JSON.stringify({ text }),
  }),
  startTimer: (durationSeconds: number) => request<{ ok: true }>('/api/control/timers', {
    method: 'POST', body: JSON.stringify({ durationSeconds }),
  }),
  cancelTimer: () => request<{ ok: true }>('/api/control/timers/current', {
    method: 'DELETE',
  }),
  reminders: async () => (
    await request<{ items: Reminder[] }>('/api/control/reminders')
  ).items,
  createReminder: (text: string, dueAt: string) => request<Reminder>(
    '/api/control/reminders',
    { method: 'POST', body: JSON.stringify({ text, dueAt }) },
  ),
  cancelReminder: (id: string) => request<{ ok: true }>(
    `/api/control/reminders/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
  ),
};
