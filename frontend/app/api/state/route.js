import { backendUrl, proxyJson } from '../_proxy';

export async function POST(request) {
  return proxyJson(request, `${backendUrl()}/api/state`, { method: 'POST' });
}
