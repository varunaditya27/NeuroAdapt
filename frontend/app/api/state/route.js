import { NextResponse } from 'next/server';

export async function POST(request) {
  const body = await request.json();
  console.log('[Observer POST]', JSON.stringify(body, null, 2));
  return NextResponse.json({ status: 'ok' });
}
