import { backendUrl, proxyJson } from '../_proxy';

export async function GET(request) {
  const url = new URL(request.url);
  return proxyJson(request, `${backendUrl()}/api/action?${url.searchParams.toString()}`, {
    method: 'GET',
  });
}
