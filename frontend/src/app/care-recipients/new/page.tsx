import OnboardingForm from '@/components/care-recipient/OnboardingForm';

export const metadata = {
  title: 'Add Care Recipient | Caregiver Co-Pilot',
  description: 'Add a new care recipient to your dashboard',
};

export default function NewCareRecipientPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 py-12 px-4 sm:px-6 lg:px-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-900 via-gray-950 to-gray-950">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400">
            Let's get started
          </h1>
          <p className="mt-4 text-lg text-gray-400">
            Tell us about the person you're caring for. We'll use this to tailor the assistant's advice.
          </p>
        </div>
        
        <OnboardingForm />
      </div>
    </div>
  );
}
