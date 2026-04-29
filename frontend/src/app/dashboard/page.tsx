import { currentUser } from '@clerk/nextjs/server'
import { UserButton } from '@clerk/nextjs'
import { redirect } from 'next/navigation'

export default async function DashboardPage() {
  const user = await currentUser()

  if (!user) {
    redirect('/sign-in')
  }

  return (
    <div className="flex flex-col min-h-screen p-8 gap-8">
      <header className="flex justify-between items-center pb-4 border-b">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <UserButton />
      </header>

      <main className="flex flex-col gap-4">
        <h2 className="text-xl">Welcome, {user.primaryEmailAddress?.emailAddress}</h2>
        <p className="text-muted-foreground">
          This is your protected dashboard. You will see your care recipients here.
        </p>
      </main>
    </div>
  )
}
