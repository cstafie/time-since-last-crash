/**
 * lib/data.ts – server-side data fetchers.
 *
 * Data is stored as JSON files in the GitHub repo and read at
 * revalidation time from raw.githubusercontent.com.
 *
 * Set GITHUB_REPO=owner/repo in your Vercel environment variables.
 * Falls back to reading local files during `next build` (useful for
 * generateStaticParams) when the env var is not set.
 */

import path from "path";
import fs from "fs/promises";
import type { Incident, StreetDetail, StreetsIndex } from "./types";

const GITHUB_REPO = process.env.GITHUB_REPO; // e.g. "octocat/time-since-last-crash"
const GITHUB_BRANCH = process.env.GITHUB_BRANCH ?? "main";

function rawUrl(filePath: string): string {
  if (!GITHUB_REPO) {
    throw new Error("GITHUB_REPO env var is not set");
  }
  return `https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/${filePath}`;
}

async function fetchJson<T>(filePath: string): Promise<T> {
  // During build on CI / Vercel, GITHUB_REPO is set — fetch from GitHub Raw.
  // During local `next build` without the env var, fall back to the local data dir.
  if (GITHUB_REPO) {
    const url = rawUrl(filePath);
    const res = await fetch(url, {
      next: { revalidate: 600 }, // 10-min fallback ISR; on-demand revalidation is primary
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch ${url}: ${res.status}`);
    }
    return res.json() as Promise<T>;
  }

  // Local fallback
  const localPath = path.join(process.cwd(), filePath);
  const text = await fs.readFile(localPath, "utf-8");
  return JSON.parse(text) as T;
}

export async function fetchStreetsIndex(): Promise<StreetsIndex> {
  try {
    return await fetchJson<StreetsIndex>("data/streets.json");
  } catch {
    return {};
  }
}

export async function fetchStreet(
  city: string,
  street: string,
): Promise<StreetDetail | null> {
  try {
    return await fetchJson<StreetDetail>(`data/streets/${city}/${street}.json`);
  } catch {
    return null;
  }
}

export async function fetchAllIncidents(): Promise<Incident[]> {
  try {
    return await fetchJson<Incident[]>("data/incidents.json");
  } catch {
    return [];
  }
}
