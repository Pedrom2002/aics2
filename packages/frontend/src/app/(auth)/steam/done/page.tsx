'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'

export default function SteamLoginDone() {
  const router = useRouter()
  const setTokens = useAuthStore((s) => s.setTokens)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const params = new URLSearchParams(window.location.hash.slice(1))
    const access = params.get('access_token')
    const refresh = params.get('refresh_token')
    if (access && refresh) {
      setTokens(access, refresh)
      window.location.hash = ''
      router.replace('/dashboard')
    } else {
      router.replace('/login?error=steam')
    }
  }, [router, setTokens])

  return <p className="text-center text-sm text-text-muted">Signing in with Steam…</p>
}
