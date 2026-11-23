
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
    try {
        const authorization = request.headers.get("authorization");

        if (!authorization?.startsWith("Bearer ")) {
            return NextResponse.json(
                { detail: "Authentication required." },
                { status: 401 }
            );
        }

        const body = await request.json();

        const response = await fetch("http://127.0.0.1:8000/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: authorization,
            },
            body: JSON.stringify(body),
            cache: "no-store",
        });

        const data = await response.json();

        return NextResponse.json(data, {
            status: response.status,
        });
    } catch {
        return NextResponse.json(
            { detail: "Unable to connect to the backend." },
            { status: 502 }
        );
    }
}
