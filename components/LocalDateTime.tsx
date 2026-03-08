"use client";

import { formatDateTime } from "@/lib/time";

interface Props {
  isoTimestamp: string;
}

export default function LocalDateTime({ isoTimestamp }: Props) {
  return <span suppressHydrationWarning>{formatDateTime(isoTimestamp)}</span>;
}
