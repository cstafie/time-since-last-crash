import Link from "next/link";
import { fetchStreetsIndex } from "@/lib/data";
import StreetSearch from "@/components/StreetSearch";
import type { Metadata } from "next";

export const revalidate = 1800;

export const metadata: Metadata = {
  title: "Recent Activity – Time Since Last Crash",
  description:
    "Streets in Metro Vancouver sorted by most recent crash, with search.",
};

export default async function RecentPage() {
  const index = await fetchStreetsIndex();
  const streets = Object.values(index).sort(
    (a, b) =>
      new Date(b.lastIncident).getTime() - new Date(a.lastIncident).getTime(),
  );

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <header className="mb-10">
        <Link
          href="/"
          className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 mb-4 inline-block"
        >
          ← Most incidents
        </Link>
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Recent Activity
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          All streets sorted by most recent crash. Use the search to filter by
          name.
        </p>
      </header>

      {streets.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">
          No incidents recorded yet. Check back after the first scrape runs.
        </p>
      ) : (
        <StreetSearch streets={streets} />
      )}
    </main>
  );
}
