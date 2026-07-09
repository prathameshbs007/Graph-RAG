import axios from 'axios';

// In production, VITE_API_URL points directly at the backend origin (e.g. the
// HF Space URL). Locally it's unset, so requests go to /api, which nginx (or
// the Vite dev proxy) forwards to the backend with the /api prefix stripped.
const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

export const api = axios.create({
  baseURL: API_BASE,
});

export function assetUrl(path: string): string {
  return `${API_BASE}${path}`;
}
