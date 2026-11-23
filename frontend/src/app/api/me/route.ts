
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
    try {
        const authorization = request.headers.get("authorization");

        if (!authorization?.startsWith("Bearer ")) {
            return NextResponse.json(
                { detail: "Authentication required." },
                { status: 401 }
            );
        }

        const response = await fetch("http://127.0.0.1:8000/me", {
            method: "GET",
            headers: {
                Authorization: authorization,
            },
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
