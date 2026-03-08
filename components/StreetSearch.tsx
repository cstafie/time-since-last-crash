"use client";

import { useState } from "react";
import Link from "next/link";
import { formatRelativeTime, formatDateTime } from "@/lib/time";
import type { StreetIndexEntry } from "@/lib/types";

interface Props {
  streets: StreetIndexEntry[];
}

export default function StreetSearch({ streets }: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const mostIncidents = [...streets]
    .sort((a, b) => b.count - a.count)
    .slice(0, 20);
  const recentStreets = [...streets]
    .sort(
      (a, b) =>
        new Date(b.lastIncident).getTime() - new Date(a.lastIncident).getTime(),
    )
    .slice(0, 20);

  const filtered = q
    ? [...streets]
        .filter((s) => s.name.toLowerCase().includes(q) || s.slug.includes(q))
        .sort(
          (a, b) =>
            new Date(b.lastIncident).getTime() -
            new Date(a.lastIncident).getTime(),
        )
    : null;

  return (
    <div>
      <div className="mb-8">
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search streets…"
          className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
        />
      </div>

      {filtered ? (
        <section>
          <h2 className="text-xl font-semibold mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
            {filtered.length === 0
              ? "No streets found"
              : `${filtered.length} street${filtered.length !== 1 ? "s" : ""} found`}
          </h2>
          {filtered.length > 0 && <StreetTable streets={filtered} showCount />}
        </section>
      ) : (
        <>
          <Section title="Most Incidents">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              Top 20 streets by total crash count
            </p>
            <StreetTable streets={mostIncidents} showCount />
          </Section>

          <Section title="Recent Activity">
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
              Streets sorted by most recent crash
            </p>
            <StreetTable streets={recentStreets} showCount />
          </Section>
        </>
      )}
    </div>
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
      <h2 className="text-xl font-semibold mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
        {title}
      </h2>
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
          <tr className="text-left text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
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
              className="border-b border-gray-100 dark:border-gray-800 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <td className="py-2 pr-4 font-medium">
                <Link
                  href={`/${s.slug}`}
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {s.name}
                </Link>
              </td>
              <td className="py-2 pr-4 text-gray-600 dark:text-gray-300 whitespace-nowrap">
                {formatDateTime(s.lastIncident)}
              </td>
              <td className="py-2 pr-4 text-gray-600 dark:text-gray-300 whitespace-nowrap">
                {formatRelativeTime(s.lastIncident)}
              </td>
              {showCount && (
                <td className="py-2">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400">
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
