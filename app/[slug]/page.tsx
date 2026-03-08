import { notFound } from "next/navigation";
import Link from "next/link";
import { fetchStreetsIndex, fetchStreet } from "@/lib/data";
import { formatDateTime, formatDuration } from "@/lib/time";
import LiveClock from "@/components/LiveClock";
import type { Metadata } from "next";

export const revalidate = 600; // 10-min fallback; on-demand revalidation is primary

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const index = await fetchStreetsIndex();
  return Object.keys(index).map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const street = await fetchStreet(slug);
  if (!street) return {};
  return {
    title: street.name,
    description: `Time since the last traffic collision on ${street.name} in Metro Vancouver. ${street.count} incident${street.count !== 1 ? "s" : ""} recorded.`,
  };
}

export default async function StreetPage({ params }: Props) {
  const { slug } = await params;
  const street = await fetchStreet(slug);

  if (!street) notFound();

  const lastIncident = street.lastIncident;

  return (
    <main className="max-w-3xl mx-auto px-4 py-10 font-sans">
      <Link
        href="/"
        className="text-sm text-gray-400 hover:text-gray-600 mb-6 inline-block"
      >
        ← All Streets
      </Link>

      {/* Hero */}
      <section className="mb-10 text-center py-12 rounded-2xl bg-gray-50 border">
        <p className="text-sm uppercase tracking-widest text-gray-400 mb-1">
          Time since last crash on
        </p>
        <h1 className="text-3xl font-bold mb-6">{street.name}</h1>

        <div className="text-5xl font-mono font-bold tabular-nums mb-2">
          <LiveClock isoTimestamp={lastIncident} />
        </div>

        {lastIncident && (
          <p className="text-sm text-gray-400 mt-3">
            Last incident:{" "}
            <time dateTime={lastIncident}>{formatDateTime(lastIncident)}</time>
          </p>
        )}

        <p className="text-sm text-gray-400 mt-1">
          {street.count} total incident{street.count !== 1 ? "s" : ""} recorded
        </p>
      </section>

      {/* Incident list */}
      <section>
        <h2 className="text-xl font-semibold mb-4 border-b pb-2">
          Incident History
        </h2>

        {street.incidents.length === 0 ? (
          <p className="text-gray-400">No incidents on record.</p>
        ) : (
          <div className="space-y-3">
            {street.incidents.map((inc) => (
              <div
                key={inc.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-lg border bg-white hover:bg-gray-50 gap-2"
              >
                <div>
                  <p className="font-medium text-sm">{inc.address}</p>
                  <p className="text-xs text-gray-400">{inc.city}</p>
                  {inc.streets.length > 1 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {inc.streets.map((s, i) => (
                        <Link
                          key={s}
                          href={`/${s}`}
                          className={`text-xs px-2 py-0.5 rounded-full border hover:bg-gray-100 ${
                            s === slug
                              ? "bg-blue-50 border-blue-200 text-blue-700"
                              : "text-gray-500"
                          }`}
                        >
                          {inc.streetNames[i]}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
                <time
                  dateTime={inc.timestamp}
                  className="text-xs text-gray-500 whitespace-nowrap shrink-0"
                >
                  {formatDateTime(inc.timestamp)}
                </time>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
