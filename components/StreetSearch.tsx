"use client";

import { useState } from "react";
import StreetTable from "@/components/StreetTable";
import type { StreetIndexEntry } from "@/lib/types";

interface Props {
  streets: StreetIndexEntry[];
}

export default function StreetSearch({ streets }: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const filtered = q
    ? [...streets]
        .filter(
          (s) =>
            s.name.toLowerCase().includes(q) ||
            s.slug.includes(q) ||
            s.city.toLowerCase().includes(q),
        )
        .sort(
          (a, b) =>
            new Date(b.lastIncident).getTime() -
            new Date(a.lastIncident).getTime(),
        )
    : streets;

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

      <section>
        <h2 className="text-xl font-semibold mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
          {q
            ? filtered.length === 0
              ? "No streets found"
              : `${filtered.length} street${filtered.length !== 1 ? "s" : ""} found`
            : "Recent Activity"}
        </h2>
        {filtered.length > 0 && (
          <StreetTable
            streets={filtered}
            defaultSort={{ key: "lastIncident", dir: "desc" }}
          />
        )}
      </section>
    </div>
  );
}
