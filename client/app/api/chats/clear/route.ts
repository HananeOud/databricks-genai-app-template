import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend-url";

export async function POST() {
  try {
    // Proxy to Python backend (DELETE /api/chats clears all)
    const response = await fetch(`${BACKEND_URL}/api/chats`, {
      method: "DELETE",
    });

    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: "Failed to clear chat history" },
        { status: response.status },
      );
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error clearing chat history:", error);
    return NextResponse.json(
      { success: false, error: "Failed to clear chat history" },
      { status: 500 },
    );
  }
}
