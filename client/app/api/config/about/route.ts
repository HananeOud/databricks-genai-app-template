import { NextResponse } from "next/server";
import { BACKEND_URL } from "@/lib/backend-url";

export async function GET() {
  try {
    // Proxy to Python backend
    const response = await fetch(`${BACKEND_URL}/api/config/about`);

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to load about configuration" },
        { status: response.status },
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error loading about config:", error);
    return NextResponse.json(
      { error: "Failed to load about configuration" },
      { status: 500 },
    );
  }
}
