"use client";

import { useEffect, useState } from "react";
import { formatDuration } from "@/lib/time";

interface Props {
  isoTimestamp: string | null;
}

/**
 * LiveClock – client component that ticks up the "time since last crash"
 * counter in real time. The server renders the initial value so there is
 * no layout shift.
 */
export default function LiveClock({ isoTimestamp }: Props) {
  const [display, setDisplay] = useState<string>(
    isoTimestamp ? formatDuration(isoTimestamp) : "No crashes recorded yet",
  );

  useEffect(() => {
    if (!isoTimestamp) return;
    const interval = setInterval(() => {
      setDisplay(formatDuration(isoTimestamp));
    }, 1000);
    return () => clearInterval(interval);
  }, [isoTimestamp]);

  return (
    <span className="tabular-nums font-mono" suppressHydrationWarning>
      {display}
    </span>
  );
}
