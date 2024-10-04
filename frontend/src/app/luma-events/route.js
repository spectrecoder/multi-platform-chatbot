import { NextResponse } from "next/server";
import fs from "fs/promises";
import path from "path";

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), "public", "luma_events.json");
    const jsonData = await fs.readFile(filePath, "utf8");
    const events = JSON.parse(jsonData);

    const formattedEvents = events.map((event) => {
      const eventData = event.event;
      const geoAddressInfo = eventData.geo_address_info || {};

      return {
        api_id: eventData.api_id,
        name: eventData.name,
        cover_url: eventData.cover_url,
        timezone: eventData.timezone,
        url: eventData.url,
        city: geoAddressInfo.city || geoAddressInfo.city_state || "",
        full_address: geoAddressInfo.full_address || "",
        start_at: eventData.start_at,
        end_at: eventData.end_at,
      };
    });

    return NextResponse.json(formattedEvents);
  } catch (error) {
    console.error("Error reading or parsing Luma events:", error);
    return NextResponse.json(
      { error: "Failed to fetch Luma events" },
      { status: 500 }
    );
  }
}
