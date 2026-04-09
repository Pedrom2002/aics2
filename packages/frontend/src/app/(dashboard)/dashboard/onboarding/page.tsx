'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { CheckCircle, Crosshair, FileUp, Rocket } from 'lucide-react'

const STEPS = [
  {
    icon: Crosshair,
    title: 'Welcome to AI CS2 Analytics',
    description:
      'Your AI-powered platform for CS2 demo analysis. We detect positioning errors, utility mistakes, and timing issues — then explain exactly how to fix them.',
  },
  {
    icon: FileUp,
    title: 'Upload Your First Demo',
    description:
      'Upload a .dem file from any CS2 match. Our pipeline will parse every round, compute player ratings, and run error detection automatically.',
  },
  {
    icon: Rocket,
    title: "You're All Set!",
    description:
      'Head to the dashboard to upload demos, track player progress, and get AI-powered insights. Your team will improve faster than ever.',
  },
]

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)
  const current = STEPS[step]
  const Icon = current.icon
  const isLast = step === STEPS.length - 1

  const handleNext = () => {
    if (isLast) {
      localStorage.setItem('onboarding_completed', 'true')
      router.push('/dashboard/demos')
    } else {
      setStep((s) => s + 1)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <div className="max-w-lg w-full text-center">
        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-2 rounded-full transition-all ${
                i === step ? 'w-8 bg-primary' : i < step ? 'w-2 bg-primary/50' : 'w-2 bg-border'
              }`}
            />
          ))}
        </div>

        <div className="bg-bg-card border border-border rounded-2xl p-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10 mb-6">
            {isLast ? (
              <CheckCircle className="h-8 w-8 text-green-400" />
            ) : (
              <Icon className="h-8 w-8 text-primary" />
            )}
          </div>

          <h1 className="text-2xl font-bold mb-3">{current.title}</h1>
          <p className="text-text-muted mb-8 leading-relaxed">{current.description}</p>

          <div className="flex items-center justify-center gap-3">
            {step > 0 && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="px-5 py-2.5 text-sm text-text-muted hover:text-text border border-border rounded-lg transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={handleNext}
              className="px-6 py-2.5 text-sm bg-primary text-white rounded-lg hover:bg-primary/80 font-medium transition-colors"
            >
              {isLast ? 'Go to Dashboard' : 'Next'}
            </button>
          </div>
        </div>

        {!isLast && (
          <button
            onClick={() => {
              localStorage.setItem('onboarding_completed', 'true')
              router.push('/dashboard')
            }}
            className="mt-4 text-xs text-text-dim hover:text-text-muted transition-colors"
          >
            Skip onboarding
          </button>
        )}
      </div>
    </div>
  )
}
