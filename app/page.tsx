import Link from "next/link";
import { fetchStreetsIndex } from "@/lib/data";
import StreetTable from "@/components/StreetTable";

export const revalidate = 1800; // 30-min fallback; on-demand revalidation is primary

export default async function Home() {
  const index = await fetchStreetsIndex();
  const top50 = Object.values(index)
    .sort((a, b) => b.count - a.count)
    .slice(0, 50);

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Time Since Last Crash
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Traffic collision incidents in Metro Vancouver, sourced from{" "}
          <a
            href="https://web.pulsepoint.org/?agencies=EMS1201"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-gray-700 dark:hover:text-gray-200"
          >
            PulsePoint BC EMS
          </a>
          . <br /> Updated every ~30 minutes. Data collection started on March
          8th 2026.
          <br /> Note that any duplicates or errors in the source data will be
          reflected here.
        </p>
      </header>

      <div className="flex items-center justify-between mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
        <h2 className="text-xl font-semibold">Most Incidents</h2>
        <Link
          href="/recent"
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          Recent activity →
        </Link>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
        Top 50 streets by total crash count
      </p>

      {top50.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">
          No incidents recorded yet. Check back after the first scrape runs.
        </p>
      ) : (
        <StreetTable
          streets={top50}
          defaultSort={{ key: "count", dir: "desc" }}
        />
      )}
    </main>
  );
}
