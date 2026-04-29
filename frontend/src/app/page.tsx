import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-background font-sans">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center gap-8 px-8">
        <h1 className="text-4xl font-bold tracking-tight text-foreground">
          Caregiver Co-Pilot
        </h1>
        <p className="text-lg text-muted-foreground text-center max-w-md">
          An AI assistant for family caregivers managing the health of a loved
          one.
        </p>
        <Button size="lg">Get Started</Button>
      </main>
    </div>
  );
}
