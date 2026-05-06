import { genEngineUrl, proxyJson } from '../_proxy';

export async function POST(request) {
  return proxyJson(request, `${genEngineUrl()}/api/generate`, { method: 'POST' });
}
