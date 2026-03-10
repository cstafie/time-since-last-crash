import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStreetsIndex, fetchStreet } from "@/lib/data";
import { formatRelativeTime, formatAveragePeriod } from "@/lib/time";
import LiveClock from "@/components/LiveClock";
import LocalDateTime from "@/components/LocalDateTime";
import type { Metadata } from "next";

export const revalidate = 600; // 10-min fallback; on-demand revalidation is primary

interface Props {
  params: Promise<{ city: string; street: string }>;
}

export async function generateStaticParams() {
  const index = await fetchStreetsIndex();
  return Object.keys(index).map((key) => {
    const [city, street] = key.split("/");
    return { city, street };
  });
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { city, street: streetSlug } = await params;
  const street = await fetchStreet(city, streetSlug);
  if (!street) return {};
  return {
    title: `${street.name}, ${street.city}`,
    description: `Time since the last traffic collision on ${street.name} in ${street.city}. ${street.count} incident${street.count !== 1 ? "s" : ""} recorded.`,
  };
}

export default async function StreetPage({ params }: Props) {
  const { city, street: streetSlug } = await params;
  const street = await fetchStreet(city, streetSlug);

  if (!street) notFound();

  const lastIncident = street.lastIncident;
  const avgPeriod = formatAveragePeriod(
    street.incidents.map((i) => i.timestamp),
  );
  const currentSlug = `${city}/${streetSlug}`;

  return (
    <main className="max-w-3xl mx-auto px-4 py-10 font-sans">
      <Link
        href="/"
        className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 mb-6 inline-block"
      >
        ← All Streets
      </Link>

      {/* Hero */}
      <section className="mb-10 text-center py-12 rounded-2xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700">
        <p className="text-sm uppercase tracking-widest text-gray-600 dark:text-gray-400 mb-1">
          Time since last crash on
        </p>
        <h1 className="text-3xl font-bold mb-6">
          {street.name}, {street.city}
        </h1>

        <div className="text-5xl font-mono font-bold tabular-nums mb-2">
          <LiveClock isoTimestamp={lastIncident} />
        </div>

        {lastIncident && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-3">
            Last incident:{" "}
            <time dateTime={lastIncident}>
              <LocalDateTime isoTimestamp={lastIncident} />
            </time>
          </p>
        )}

        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {street.count} total incident{street.count !== 1 ? "s" : ""} recorded
        </p>

        {avgPeriod && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Avg. time between incidents:{" "}
            <span className="font-medium text-gray-800 dark:text-gray-200">
              {avgPeriod}
            </span>
          </p>
        )}
      </section>

      {/* Incident list */}
      <section>
        <h2 className="text-xl font-semibold mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
          Incident History
        </h2>

        {street.incidents.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">
            No incidents on record.
          </p>
        ) : (
          <div className="space-y-3">
            {street.incidents.map((inc) => (
              <div
                key={inc.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 gap-2"
              >
                <div>
                  <p className="font-medium text-sm dark:text-gray-100">
                    {inc.address}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {inc.city}
                  </p>
                  {inc.streets.length > 1 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {inc.streets.map((s, i) => (
                        <Link
                          key={s}
                          href={`/${s}`}
                          className={`text-xs px-2 py-0.5 rounded-full border hover:bg-gray-100 dark:hover:bg-gray-700 ${
                            s === currentSlug
                              ? "bg-blue-50 border-blue-200 text-blue-700 dark:bg-blue-950 dark:border-blue-800 dark:text-blue-300"
                              : "text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-600"
                          }`}
                        >
                          {inc.streetNames[i]}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
                <div className="text-right shrink-0">
                  <time
                    dateTime={inc.timestamp}
                    className="block text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap"
                  >
                    <LocalDateTime isoTimestamp={inc.timestamp} />
                  </time>
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    {formatRelativeTime(inc.timestamp)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
