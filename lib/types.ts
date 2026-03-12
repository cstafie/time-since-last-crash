/**
 * lib/types.ts – shared TypeScript types for incidents and streets.
 */

export interface Incident {
  id: string;
  pulsePointId?: string;
  timestamp: string; // ISO 8601, Pacific time
  scrapedAt: string;
  address: string;
  city: string;
  streets: string[]; // slugs
  streetNames: string[]; // display names
  raw?: string;
}

export interface StreetIndexEntry {
  name: string;
  slug: string;
  city: string;
  lastIncident: string; // ISO 8601
  count: number;
}

export interface StreetDetail {
  slug: string;
  name: string;
  city: string;
  lastIncident: string | null;
  count: number;
  incidents: Omit<Incident, "raw">[];
}

export type StreetsIndex = Record<string, StreetIndexEntry>;
