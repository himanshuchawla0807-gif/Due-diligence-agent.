import { API_BASE_URL, SESSION_SERVICE_URL } from '@/config';

let token = new URLSearchParams(window.location.search).get('token') || '';
if (token) {
  const url = new URL(window.location.href);
  url.searchParams.delete('token');
  window.history.replaceState(null, '', url);
}
window.addEventListener('message', event => {
  const trusted = ['https://oriplex.tech', 'https://app.oriplex.tech',
    'https://universal-frontend-2ej63xd5fa-ew.a.run.app', 'https://oriplex-frontend-2ej63xd5fa-ew.a.run.app'];
  if (['localhost', '127.0.0.1'].includes(window.location.hostname)) trusted.push('http://localhost:3000');
  if (event.source === window.parent && trusted.includes(event.origin) &&
      event.data?.type === 'tokenRefresh' && typeof event.data.token === 'string') token = event.data.token;
});

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const url = new URL(input instanceof Request ? input.url : String(input), window.location.href);
  const trusted = [API_BASE_URL, SESSION_SERVICE_URL].some(base => new URL(base).origin === url.origin);
  const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
  if (trusted && !token && !url.pathname.endsWith('/health')) {
    await new Promise<void>((resolve, reject) => {
      const cleanup = () => { clearTimeout(timer); window.removeEventListener('message', ready); };
      const ready = () => queueMicrotask(() => { if (token) { cleanup(); resolve(); } });
      const timer = setTimeout(() => { cleanup(); reject(new Error('Sign in before accessing documents')); }, 10000);
      window.addEventListener('message', ready);
    });
  }
  if (trusted && token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
