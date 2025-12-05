import { NextRequest, NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend-url";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;

    // Proxy to Python backend
    const response = await fetch(`${BACKEND_URL}/api/chats/${id}`);

    if (!response.ok) {
      return NextResponse.json(
        { error: "Chat not found" },
        { status: response.status },
      );
    }

    const chat = await response.json();
    return NextResponse.json(chat);
  } catch (error) {
    console.error("Error fetching chat:", error);
    return NextResponse.json(
      { error: "Failed to fetch chat" },
      { status: 500 },
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;

    // Proxy to Python backend
    const response = await fetch(`${BACKEND_URL}/api/chats/${id}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to delete chat" },
        { status: response.status },
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error deleting chat:", error);
    return NextResponse.json(
      { error: "Failed to delete chat" },
      { status: 500 },
    );
  }
}
