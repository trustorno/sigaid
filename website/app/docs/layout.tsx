import { Header } from "@/components/landing/Header";
import { DocsSidebar } from "@/components/docs/DocsSidebar";

export default function DocsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header />
      <div className="flex min-h-screen pt-16">
        <DocsSidebar />
        <main className="flex-1 max-w-4xl mx-auto px-6 py-12">
          {children}
        </main>
      </div>
    </>
  );
}
