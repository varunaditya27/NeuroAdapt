import { NextResponse } from 'next/server';

const DEFAULT_BACKEND_URL = 'http://localhost:8000';
const DEFAULT_GEN_ENGINE_URL = 'http://localhost:8001';

export function backendUrl() {
  return process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL;
}

export function genEngineUrl() {
  return (
    process.env.GEN_ENGINE_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_GEN_ENGINE_URL ||
    DEFAULT_GEN_ENGINE_URL
  );
}

export async function proxyJson(request, targetUrl, init = {}) {
  const method = init.method || request.method;
  const headers = { 'Content-Type': 'application/json', ...(init.headers || {}) };
  const body = init.body !== undefined ? init.body : method === 'GET' ? undefined : await request.text();

  try {
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
      cache: 'no-store',
    });

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : { detail: await response.text() };

    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      { detail: `Proxy request failed: ${error instanceof Error ? error.message : String(error)}` },
      { status: 502 }
    );
  }
}
