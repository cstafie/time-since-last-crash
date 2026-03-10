"use client";

import { useEffect, useState } from "react";
import { formatDateTime } from "@/lib/time";

interface Props {
  isoTimestamp: string;
}

export default function LocalDateTime({ isoTimestamp }: Props) {
  const [display, setDisplay] = useState(isoTimestamp);

  useEffect(() => {
    setDisplay(formatDateTime(isoTimestamp));
  }, [isoTimestamp]);

  return <span suppressHydrationWarning>{display}</span>;
}
