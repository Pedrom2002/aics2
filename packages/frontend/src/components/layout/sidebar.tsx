'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  BarChart3,
  Crosshair,
  FileUp,
  Home,
  Menu,
  Settings,
  Trophy,
  Users,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

import { useState } from 'react'

const navItems = [
  { href: '/dashboard', label: 'Overview', icon: Home },
  { href: '/dashboard/demos', label: 'Demos', icon: FileUp },
  { href: '/dashboard/pro', label: 'Pro Matches', icon: Trophy },
  { href: '/dashboard/players', label: 'Players', icon: Users },
  { href: '/dashboard/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const navContent = (
    <>
      <div className="h-16 flex items-center justify-between px-5 border-b border-border">
        <Link href="/dashboard" className="flex items-center gap-2 font-bold">
          <Crosshair className="h-5 w-5 text-primary" />
          <span className="text-sm">AI CS2 Analytics</span>
        </Link>
        <button
          onClick={() => setMobileOpen(false)}
          className="md:hidden p-1 text-text-muted"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-primary-dim text-primary font-medium'
                  : 'text-text-muted hover:text-text hover:bg-bg-elevated'
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </>
  )

  return (
    <>
      {/* Mobile hamburger button */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 md:hidden p-2 bg-bg-card border border-border rounded-lg"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-60 border-r border-border bg-bg-card flex flex-col transition-transform md:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {navContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-60 border-r border-border bg-bg-card flex-col h-screen sticky top-0">
        {navContent}
      </aside>
    </>
  )
}
