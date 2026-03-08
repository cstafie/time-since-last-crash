"use client";

import Link from "next/link";
import { formatRelativeTime, formatDateTime } from "@/lib/time";
import type { StreetIndexEntry } from "@/lib/types";

export default function StreetTable({
  streets,
}: {
  streets: StreetIndexEntry[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider border-b border-gray-200 dark:border-gray-700">
            <th className="pb-2 pr-4 font-medium">Street</th>
            <th className="pb-2 pr-4 font-medium">Last Crash</th>
            <th className="pb-2 pr-4 font-medium">Time Since</th>
            <th className="pb-2 font-medium">Total</th>
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
