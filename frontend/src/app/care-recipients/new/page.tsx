import OnboardingForm from '@/components/care-recipient/OnboardingForm';

export const metadata = {
  title: 'Add Care Recipient | Caregiver Co-Pilot',
  description: 'Add a new care recipient to your dashboard',
};

export default function NewCareRecipientPage() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl text-gray-900">
            Let's get started
          </h1>
          <p className="mt-4 text-lg text-gray-600">
            Tell us about the person you're caring for. We'll use this to tailor the assistant's advice.
          </p>
        </div>
        
        <OnboardingForm />
      </div>
    </div>
  );
}
