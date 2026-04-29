import { Button } from "@/components/ui/button";
import Link from "next/link";
import { UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";

export default async function Home() {
  const { userId } = await auth();

  return (
    <div className="flex flex-col flex-1 min-h-screen bg-background font-sans">
      <header className="flex items-center justify-between p-6 w-full">
        <div className="font-bold text-xl tracking-tight">Caregiver Co-Pilot</div>
        <div className="flex gap-4 items-center">
          {userId ? (
            <>
              <Link href="/dashboard">
                <Button variant="ghost">Dashboard</Button>
              </Link>
              <UserButton />
            </>
          ) : (
            <Link href="/sign-in">
              <Button variant="ghost">Sign In</Button>
            </Link>
          )}
        </div>
      </header>

      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center gap-8 px-8 mx-auto -mt-20">
        <h1 className="text-5xl font-bold tracking-tight text-foreground text-center">
          Caregiver Co-Pilot
        </h1>
        <p className="text-xl text-muted-foreground text-center max-w-lg">
          An AI assistant for family caregivers managing the health of a loved one.
        </p>
        {userId ? (
          <Link href="/dashboard">
            <Button size="lg" className="px-8 text-lg">Go to Dashboard</Button>
          </Link>
        ) : (
          <Link href="/sign-up">
            <Button size="lg" className="px-8 text-lg">Get Started</Button>
          </Link>
        )}
      </main>
    </div>
  );
}
