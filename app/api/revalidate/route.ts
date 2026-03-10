import { NextRequest, NextResponse } from "next/server";
import { revalidatePath } from "next/cache";

/**
 * POST /api/revalidate
 *
 * Called by the GitHub Actions scraper workflow after committing new data.
 * Triggers on-demand ISR revalidation for the homepage and any changed street pages.
 *
 * Body: { all?: true } | { slugs?: string[] }
 * Header: Authorization: Bearer <REVALIDATE_SECRET>
 */
export async function POST(req: NextRequest) {
  const secret = process.env.REVALIDATE_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "REVALIDATE_SECRET not configured" },
      { status: 500 },
    );
  }

  const authHeader = req.headers.get("authorization");
  const provided = authHeader?.startsWith("Bearer ")
    ? authHeader.slice(7)
    : null;

  if (!provided || provided !== secret) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { all?: boolean; slugs?: string[] } = {};
  try {
    body = await req.json();
  } catch {
    // empty body — treat as revalidate all
    body = { all: true };
  }

  // Always revalidate the homepage
  revalidatePath("/");

  const revalidatedSlugs: string[] = [];

  if (body.all) {
    // Revalidate the entire [city]/[street] dynamic segment
    revalidatePath("/[city]/[street]", "page");
    revalidatedSlugs.push("*");
  } else if (Array.isArray(body.slugs) && body.slugs.length > 0) {
    for (const slug of body.slugs) {
      // slugs are now "city-slug/street-slug"
      if (typeof slug === "string" && /^[\w-]+\/[\w-]+$/.test(slug)) {
        revalidatePath(`/${slug}`);
        revalidatedSlugs.push(slug);
      }
    }
  }

  return NextResponse.json({
    revalidated: true,
    slugs: revalidatedSlugs,
    timestamp: new Date().toISOString(),
  });
}
