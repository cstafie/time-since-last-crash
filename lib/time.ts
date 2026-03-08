/**
 * lib/time.ts – shared time-formatting utilities (safe for server + client).
 */

export function formatRelativeTime(isoTimestamp: string): string {
  const then = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();

  if (diffMs < 0) return "just now";

  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days} day${days !== 1 ? "s" : ""} ago`;
  if (hours > 0) return `${hours} hour${hours !== 1 ? "s" : ""} ago`;
  if (minutes > 0) return `${minutes} minute${minutes !== 1 ? "s" : ""} ago`;
  return `${seconds} second${seconds !== 1 ? "s" : ""} ago`;
}

export function formatDuration(isoTimestamp: string): string {
  const then = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - then.getTime();

  if (diffMs < 0) return "0 seconds";

  const totalSeconds = Math.floor(diffMs / 1000);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const totalHours = Math.floor(totalMinutes / 60);
  const hours = totalHours % 24;
  const days = Math.floor(totalHours / 24);

  if (days > 0) {
    return `${days}d ${hours}h ${minutes}m`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

export function formatAveragePeriod(isoTimestamps: string[]): string | null {
  if (isoTimestamps.length < 4) return null;

  const sorted = isoTimestamps
    .map((t) => new Date(t).getTime())
    .sort((a, b) => a - b);

  const avgMs = (sorted[sorted.length - 1] - sorted[0]) / (sorted.length - 1);

  const totalMinutes = Math.floor(avgMs / 60_000);
  const totalHours = Math.floor(totalMinutes / 60);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const minutes = totalMinutes % 60;

  if (days >= 1) {
    return hours > 0
      ? `${days}d ${hours}h`
      : `${days} day${days !== 1 ? "s" : ""}`;
  }
  if (totalHours >= 1) {
    return minutes > 0 ? `${totalHours}h ${minutes}m` : `${totalHours}h`;
  }
  return `${totalMinutes} min`;
}

export function formatDateTime(isoTimestamp: string): string {
  return new Date(isoTimestamp).toLocaleString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}
