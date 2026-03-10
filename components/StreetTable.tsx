"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { formatRelativeTime, formatDateTime } from "@/lib/time";
import type { StreetIndexEntry } from "@/lib/types";

type SortKey = "name" | "lastIncident" | "count";
type SortDir = "asc" | "desc";

function SortArrow({ active, dir }: { active: boolean; dir: SortDir }) {
  if (!active)
    return <span className="ml-1 opacity-0 group-hover:opacity-40">↕</span>;
  return <span className="ml-1">{dir === "asc" ? "↑" : "↓"}</span>;
}

export default function StreetTable({
  streets,
  defaultSort,
}: {
  streets: StreetIndexEntry[];
  defaultSort?: { key: SortKey; dir: SortDir };
}) {
  const [sortKey, setSortKey] = useState<SortKey | null>(
    defaultSort?.key ?? null,
  );
  const [sortDir, setSortDir] = useState<SortDir>(defaultSort?.dir ?? "desc");

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "name" ? "asc" : "desc");
    }
  }

  const sorted = useMemo(() => {
    if (!sortKey) return streets;
    const copy = [...streets];
    const dir = sortDir === "asc" ? 1 : -1;
    copy.sort((a, b) => {
      if (sortKey === "name") return dir * a.name.localeCompare(b.name);
      if (sortKey === "lastIncident")
        return (
          dir *
          (new Date(a.lastIncident).getTime() -
            new Date(b.lastIncident).getTime())
        );
      return dir * (a.count - b.count);
    });
    return copy;
  }, [streets, sortKey, sortDir]);

  const thClass =
    "pb-2 pr-4 font-medium cursor-pointer select-none group hover:text-gray-700 dark:hover:text-gray-200 transition-colors";

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
            <th className={thClass} onClick={() => handleSort("name")}>
              Street
              <SortArrow active={sortKey === "name"} dir={sortDir} />
            </th>
            <th className={thClass} onClick={() => handleSort("lastIncident")}>
              Last Crash
              <SortArrow active={sortKey === "lastIncident"} dir={sortDir} />
            </th>
            <th className={thClass} onClick={() => handleSort("lastIncident")}>
              Time Since
              <SortArrow active={sortKey === "lastIncident"} dir={sortDir} />
            </th>
            <th
              className={`${thClass} pr-0!`}
              onClick={() => handleSort("count")}
            >
              Total
              <SortArrow active={sortKey === "count"} dir={sortDir} />
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => (
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
              <td className="py-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400">
                  {s.count}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
