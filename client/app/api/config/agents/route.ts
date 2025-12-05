import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend-url";

export async function GET() {
  try {
    // Proxy to Python backend
    const response = await fetch(`${BACKEND_URL}/api/config/agents`);

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to load agents" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error loading agents:", error);
    return NextResponse.json(
      { error: "Failed to load agents" },
      { status: 500 },
    );
  }
}
