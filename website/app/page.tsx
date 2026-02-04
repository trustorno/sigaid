import {
  Header,
  Hero,
  Problem,
  Solution,
  CodeExamples,
  UseCases,
  Security,
  Pricing,
  Footer,
} from "@/components/landing";

export default function Home() {
  return (
    <>
      <Header />
      <main>
        <Hero />
        <Problem />
        <Solution />
        <CodeExamples />
        <UseCases />
        <Security />
        <Pricing />
      </main>
      <Footer />
    </>
  );
}
