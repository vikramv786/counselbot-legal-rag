
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();

        const response = await fetch(
            "http://127.0.0.1:8000/demo/chat",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(body),
                cache: "no-store",
            }
        );

        const data = await response.json();

        return NextResponse.json(data, {
            status: response.status,
        });
    } catch (error) {
        console.error("Chat API proxy error:", error);

        return NextResponse.json(
            {
                detail: "Unable to connect to the CounselBot backend.",
            },
            {
                status: 502,
            }
        );
    }
}
