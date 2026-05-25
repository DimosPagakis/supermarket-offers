import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Σχετικά",
  description: "Τι είναι το Προσφορές Σούπερ Μάρκετ και πώς λειτουργεί.",
};

export default function AboutPage() {
  return (
    <article className="prose prose-zinc mx-auto max-w-3xl dark:prose-invert">
      <h1 className="text-3xl font-bold tracking-tight">Σχετικά</h1>

      <p className="mt-4 text-zinc-700 dark:text-zinc-300">
        Το <strong>Προσφορές Σούπερ Μάρκετ</strong> συγκεντρώνει τις τρέχουσες
        εβδομαδιαίες προσφορές από τις μεγαλύτερες ελληνικές αλυσίδες σούπερ
        μάρκετ σε μία ενιαία λίστα — ώστε να βρίσκεις τη φθηνότερη τιμή χωρίς
        να ανοίγεις πέντε διαφορετικά site.
      </p>

      <h2 className="mt-8 text-xl font-semibold">Από πού έρχονται τα δεδομένα;</h2>
      <p className="text-zinc-700 dark:text-zinc-300">
        Συλλέγουμε δημόσια διαθέσιμα φυλλάδια προσφορών από τις παρακάτω αλυσίδες:
      </p>
      <ul className="list-disc pl-5 text-zinc-700 dark:text-zinc-300">
        <li>AB Βασιλόπουλος</li>
        <li>Σκλαβενίτης</li>
        <li>Lidl Hellas</li>
        <li>My Market</li>
        <li>Μασούτης</li>
      </ul>
      <p className="text-zinc-700 dark:text-zinc-300">
        Δεν είμαστε συνδεδεμένοι με καμία από αυτές τις εταιρείες. Όλες οι
        ονομασίες και τα λογότυπα ανήκουν στους ιδιοκτήτες τους.
      </p>

      <h2 className="mt-8 text-xl font-semibold">Ανοιχτό API</h2>
      <p className="text-zinc-700 dark:text-zinc-300">
        Τα δεδομένα είναι διαθέσιμα δωρεάν μέσω ενός δημόσιου REST API. Εάν
        φτιάχνεις δική σου εφαρμογή — π.χ. λίστα αγορών, υπηρεσία ειδοποιήσεων
        ή εργαλείο ανάλυσης τιμών — μπορείς να χτυπήσεις τα ίδια endpoints που
        χρησιμοποιεί και αυτό το site:
      </p>
      <pre className="overflow-x-auto rounded-md bg-zinc-100 p-3 text-xs dark:bg-zinc-800">
{`GET /api/public/v1/offers
GET /api/public/v1/offers/{id}
GET /api/public/v1/brands
GET /api/public/v1/categories
GET /api/public/v1/brands/{slug}/offers
GET /api/public/v1/search?q=...`}
      </pre>
      <p className="text-zinc-700 dark:text-zinc-300">
        Όριο: 120 αιτήματα ανά λεπτό ανά IP.
      </p>

      <h2 className="mt-8 text-xl font-semibold">Πηγαίος κώδικας</h2>
      <p className="text-zinc-700 dark:text-zinc-300">
        Το project είναι open source. Δες τον κώδικα στο{" "}
        <a
          href="https://github.com/"
          target="_blank"
          rel="noreferrer noopener"
          className="text-emerald-600 underline"
        >
          GitHub
        </a>
        .
      </p>

      <p className="mt-8 text-sm text-zinc-500">
        <Link href="/" className="underline">
          ← Επιστροφή στην αρχική
        </Link>
      </p>
    </article>
  );
}
