import { fetchStreetsIndex } from "@/lib/data";
import StreetSearch from "@/components/StreetSearch";

export const revalidate = 30 * 60; // 30-min fallback; on-demand revalidation is primary

export default async function Home() {
  const index = await fetchStreetsIndex();
  const streets = Object.values(index);

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
