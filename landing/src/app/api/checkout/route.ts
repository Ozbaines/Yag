import { NextRequest, NextResponse } from "next/server";

const PAYMENTS_API = process.env.PAYMENTS_API_URL ?? "http://payments:8000";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${PAYMENTS_API}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
