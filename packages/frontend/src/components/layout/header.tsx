'use client'

import { useRouter } from 'next/navigation'
import { LogOut, Moon, Sun, User } from 'lucide-react'
import { useAuthStore } from '@/stores/auth-store'
import { useTheme } from '@/lib/theme'

export function Header() {
  const router = useRouter()
  const { user, organization, logout } = useAuthStore()
  const { theme, toggle } = useTheme()

  async function handleLogout() {
    await logout()
    router.push('/')
  }

  return (
    <header className="h-16 border-b border-border bg-bg-card px-6 flex items-center justify-between">
      <div>
        <span className="text-sm text-text-muted">{organization?.name}</span>
      </div>
      <div className="flex items-center gap-4">
        <button
          onClick={toggle}
          className="text-text-muted hover:text-text transition-colors p-1"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <div className="flex items-center gap-2 text-sm">
          <User className="h-4 w-4 text-text-muted" />
          <span>{user?.display_name}</span>
          <span className="text-xs bg-bg-elevated text-text-muted px-2 py-0.5 rounded">
            {user?.role}
          </span>
        </div>
        <button
          onClick={handleLogout}
          className="text-text-muted hover:text-danger transition-colors p-1"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  )
}
