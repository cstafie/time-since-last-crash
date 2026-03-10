import Link from "next/link";
import { fetchStreetsIndex } from "@/lib/data";
import StreetSearch from "@/components/StreetSearch";
import type { Metadata } from "next";

export const revalidate = 1800;

interface Props {
  params: Promise<{ city: string }>;
}

export async function generateStaticParams() {
  const index = await fetchStreetsIndex();
  const cities = new Set<string>();
  for (const entry of Object.values(index)) {
    cities.add(entry.slug.split("/")[0]);
  }
  return [...cities].map((city) => ({ city }));
}

function titleCase(slug: string): string {
  return slug
    .split("-")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { city } = await params;
  const cityName = titleCase(city);
  return {
    title: `${cityName} – Time Since Last Crash`,
    description: `Traffic collision incidents in ${cityName}, sorted by most recent crash.`,
  };
}

export default async function CityPage({ params }: Props) {
  const { city } = await params;
  const index = await fetchStreetsIndex();
  const cityName = titleCase(city);

  const streets = Object.values(index)
    .filter((s) => s.slug.startsWith(`${city}/`))
    .sort(
      (a, b) =>
        new Date(b.lastIncident).getTime() - new Date(a.lastIncident).getTime(),
    );

  return (
    <main className="max-w-4xl mx-auto px-4 py-10">
      <header className="mb-10">
        <Link
          href="/"
          className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 mb-4 inline-block"
        >
          ← All streets
        </Link>
        <h1 className="text-3xl font-bold tracking-tight mb-2">{cityName}</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {streets.length} street{streets.length !== 1 ? "s" : ""} with recorded
          incidents. Sorted by most recent crash.
        </p>
      </header>

      {streets.length === 0 ? (
        <p className="text-gray-500 dark:text-gray-400">
          No incidents recorded in {cityName} yet.
        </p>
      ) : (
        <StreetSearch streets={streets} />
      )}
    </main>
  );
}
