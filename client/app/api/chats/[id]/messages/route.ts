import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend-url";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const body = await request.json();

    // Proxy to Python backend
    const response = await fetch(
      `${BACKEND_URL}/api/chats/${id}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to save messages" },
        { status: response.status },
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error saving messages:", error);
    return NextResponse.json(
      { error: "Failed to save messages" },
      { status: 500 },
    );
  }
}
