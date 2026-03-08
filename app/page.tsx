import Link from "next/link";
import { fetchStreetsIndex } from "@/lib/data";
import { formatRelativeTime, formatDateTime } from "@/lib/time";
import type { StreetIndexEntry } from "@/lib/types";

export const revalidate = 600; // 10-min fallback; on-demand revalidation is primary

export default async function Home() {
  const index = await fetchStreetsIndex();
  const streets: StreetIndexEntry[] = Object.values(index);

  const recentStreets = [...streets].sort(
    (a, b) =>
      new Date(b.lastIncident).getTime() - new Date(a.lastIncident).getTime(),
  );

  const dangerousStreets = [...streets]
    .sort((a, b) => b.count - a.count)
    .slice(0, 20);

  return (
    <main className="max-w-4xl mx-auto px-4 py-10 font-sans">
      <header className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight mb-2">
          Time Since Last Crash
        </h1>
        <p className="text-gray-500 text-sm">
          Traffic collision incidents in Metro Vancouver, sourced from{" "}
          <a
            href="https://web.pulsepoint.org/?agencies=EMS1201"
            target="_blank"
            rel="noopener noreferrer"
            className="underline"
          >
            PulsePoint BC EMS
          </a>
          . Updated every 5 minutes.
        </p>
      </header>

      {streets.length === 0 ? (
        <p className="text-gray-400">
          No incidents recorded yet. Check back after the first scrape runs.
        </p>
      ) : (
        <>
          <Section title="Recent Activity">
            <p className="text-xs text-gray-400 mb-3">
              Streets sorted by most recent crash
            </p>
            <StreetTable streets={recentStreets} />
          </Section>

          <Section title="Most Incidents">
            <p className="text-xs text-gray-400 mb-3">
              Top 20 streets by total crash count
            </p>
            <StreetTable streets={dangerousStreets} showCount />
          </Section>
        </>
      )}
    </main>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-12">
      <h2 className="text-xl font-semibold mb-4 border-b pb-2">{title}</h2>
      {children}
    </section>
  );
}

function StreetTable({
  streets,
  showCount = false,
}: {
  streets: StreetIndexEntry[];
  showCount?: boolean;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 text-xs uppercase tracking-wider border-b">
            <th className="pb-2 pr-4 font-medium">Street</th>
            <th className="pb-2 pr-4 font-medium">Last Crash</th>
            <th className="pb-2 pr-4 font-medium">Time Since</th>
            {showCount && <th className="pb-2 font-medium">Total</th>}
          </tr>
        </thead>
        <tbody>
          {streets.map((s) => (
            <tr
              key={s.slug}
              className="border-b last:border-0 hover:bg-gray-50"
            >
              <td className="py-2 pr-4 font-medium">
                <Link
                  href={`/${s.slug}`}
                  className="text-blue-600 hover:underline"
                >
                  {s.name}
                </Link>
              </td>
              <td className="py-2 pr-4 text-gray-600 whitespace-nowrap">
                {formatDateTime(s.lastIncident)}
              </td>
              <td className="py-2 pr-4 text-gray-600 whitespace-nowrap">
                {formatRelativeTime(s.lastIncident)}
              </td>
              {showCount && (
                <td className="py-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                    {s.count}
                  </span>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
