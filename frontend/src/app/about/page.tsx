import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Σχετικά",
  description: "Τι είναι το Προσφορές Σούπερ Μάρκετ και πώς λειτουργεί.",
};

export default function AboutPage() {
  return (
    <article className="mx-auto max-w-3xl">
      <h1 className="text-3xl font-bold tracking-tight text-ink">Σχετικά</h1>

      <p className="mt-4 text-ink-soft">
        Το <strong className="text-ink">Προσφορές Σούπερ Μάρκετ</strong> συγκεντρώνει
        τις τρέχουσες εβδομαδιαίες προσφορές από τις μεγαλύτερες ελληνικές αλυσίδες
        σούπερ μάρκετ σε μία ενιαία λίστα — ώστε να βρίσκεις τη φθηνότερη τιμή χωρίς
        να ανοίγεις πέντε διαφορετικά site.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-ink">Από πού έρχονται τα δεδομένα;</h2>
      <p className="mt-2 text-ink-soft">
        Συλλέγουμε δημόσια διαθέσιμα φυλλάδια προσφορών από τις παρακάτω αλυσίδες:
      </p>
      <ul className="mt-2 list-disc pl-5 text-ink-soft">
        <li>AB Βασιλόπουλος</li>
        <li>Σκλαβενίτης</li>
        <li>Lidl Hellas</li>
        <li>My Market</li>
        <li>Μασούτης</li>
      </ul>
      <p className="mt-2 text-ink-soft">
        Δεν είμαστε συνδεδεμένοι με καμία από αυτές τις εταιρείες. Όλες οι
        ονομασίες και τα λογότυπα ανήκουν στους ιδιοκτήτες τους.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-ink">Ανοιχτό API</h2>
      <p className="mt-2 text-ink-soft">
        Τα δεδομένα είναι διαθέσιμα δωρεάν μέσω ενός δημόσιου REST API. Εάν
        φτιάχνεις δική σου εφαρμογή — π.χ. λίστα αγορών, υπηρεσία ειδοποιήσεων
        ή εργαλείο ανάλυσης τιμών — μπορείς να χτυπήσεις τα ίδια endpoints που
        χρησιμοποιεί και αυτό το site:
      </p>
      <pre className="mt-3 overflow-x-auto rounded-[var(--radius-card)] border border-border bg-canvas-muted p-4 text-xs text-ink">
{`GET /api/public/v1/offers
GET /api/public/v1/offers/{id}
GET /api/public/v1/brands
GET /api/public/v1/categories
GET /api/public/v1/brands/{slug}/offers
GET /api/public/v1/search?q=...`}
      </pre>
      <p className="mt-2 text-ink-soft">
        Όριο: 120 αιτήματα ανά λεπτό ανά IP.
      </p>

      <h2 className="mt-8 text-xl font-semibold text-ink">Πηγαίος κώδικας</h2>
      <p className="mt-2 text-ink-soft">
        Το project είναι open source. Δες τον κώδικα στο{" "}
        <a
          href="https://github.com/"
          target="_blank"
          rel="noreferrer noopener"
          className="font-medium text-brand underline-offset-2 hover:underline"
        >
          GitHub
        </a>
        .
      </p>

      <p className="mt-8 text-sm">
        <Link
          href="/"
          className="font-medium text-brand underline-offset-2 hover:underline"
        >
          ← Επιστροφή στην αρχική
        </Link>
      </p>
    </article>
  );
}
