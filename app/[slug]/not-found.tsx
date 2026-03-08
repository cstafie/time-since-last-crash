import Link from "next/link";

export default function NotFound() {
  return (
    <main className="max-w-3xl mx-auto px-4 py-20 font-sans text-center">
      <h1 className="text-4xl font-bold mb-4">Street Not Found</h1>
      <p className="text-gray-500 dark:text-gray-400 mb-8">
        No crash data has been recorded for this street yet.
      </p>
      <Link href="/" className="text-blue-600 dark:text-blue-400 underline">
        ← Back to all streets
      </Link>
    </main>
  );
}
