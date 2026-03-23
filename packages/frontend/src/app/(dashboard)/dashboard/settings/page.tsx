'use client'

import { useState } from 'react'
import {
  CreditCard,
  Settings,
  Shield,
  UserPlus,
  Users,
} from 'lucide-react'

// Pricing tiers
const TIERS = [
  { id: 'free', name: 'Free', price: 0, demos: 10, seats: 1 },
  { id: 'solo', name: 'Solo', price: 9, demos: 15, seats: 1 },
  { id: 'team', name: 'Team', price: 39, demos: 30, seats: 5 },
  { id: 'pro', name: 'Pro', price: 129, demos: -1, seats: 15 },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'general' | 'team' | 'billing'>('general')
  const [orgName, setOrgName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [currentTier, setCurrentTier] = useState('free')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const tabs = [
    { id: 'general' as const, label: 'General', icon: Settings },
    { id: 'team' as const, label: 'Team', icon: Users },
    { id: 'billing' as const, label: 'Billing', icon: CreditCard },
  ]

  const handleSaveOrg = async () => {
    setSaving(true)
    setMessage(null)
    try {
      // In production: PUT /api/v1/org to update org name
      setMessage('Settings saved successfully')
    } catch {
      setMessage('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleInvite = async () => {
    if (!inviteEmail) return
    setSaving(true)
    setMessage(null)
    try {
      // In production: POST /api/v1/auth/invite
      setMessage(`Invitation sent to ${inviteEmail}`)
      setInviteEmail('')
    } catch {
      setMessage('Failed to send invitation')
    } finally {
      setSaving(false)
    }
  }

  const handleUpgrade = async (tierId: string) => {
    try {
      // In production: POST /api/v1/billing/checkout → Stripe Checkout URL
      setMessage(`Upgrade to ${tierId} — Stripe Checkout would open here`)
    } catch {
      setMessage('Failed to start checkout')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Settings className="h-6 w-6 text-primary" />
        Settings
      </h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {message && (
        <div className="mb-4 px-4 py-2 bg-primary/10 border border-primary/20 rounded-lg text-sm text-primary">
          {message}
        </div>
      )}

      {/* General Settings */}
      {activeTab === 'general' && (
        <div className="bg-bg-card border border-border rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Organization Name</label>
            <input
              type="text"
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
              placeholder="My Team"
              className="w-full max-w-md px-3 py-2 bg-bg-elevated border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">Timezone</label>
            <select className="px-3 py-2 bg-bg-elevated border border-border rounded-lg text-sm focus:outline-none focus:border-primary">
              <option value="UTC">UTC</option>
              <option value="Europe/Lisbon">Europe/Lisbon</option>
              <option value="Europe/London">Europe/London</option>
              <option value="Europe/Berlin">Europe/Berlin</option>
              <option value="America/Sao_Paulo">America/Sao_Paulo</option>
              <option value="America/New_York">America/New_York</option>
            </select>
          </div>
          <button
            onClick={handleSaveOrg}
            disabled={saving}
            className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary/80 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      )}

      {/* Team Management */}
      {activeTab === 'team' && (
        <div className="space-y-4">
          <div className="bg-bg-card border border-border rounded-xl p-6">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-primary" />
              Invite Member
            </h2>
            <div className="flex gap-2">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="teammate@example.com"
                className="flex-1 max-w-md px-3 py-2 bg-bg-elevated border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
              />
              <button
                onClick={handleInvite}
                disabled={saving || !inviteEmail}
                className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary/80 disabled:opacity-50"
              >
                Send Invite
              </button>
            </div>
          </div>

          <div className="bg-bg-card border border-border rounded-xl p-6">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              Team Roster
            </h2>
            <p className="text-text-dim text-sm">
              Team members will appear here once they accept invitations.
            </p>
          </div>
        </div>
      )}

      {/* Billing */}
      {activeTab === 'billing' && (
        <div className="space-y-4">
          <div className="bg-bg-card border border-border rounded-xl p-6 mb-4">
            <h2 className="text-lg font-bold mb-2">Current Plan</h2>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-primary capitalize">{currentTier}</span>
              <span className="text-text-dim text-sm">
                {TIERS.find((t) => t.id === currentTier)?.demos === -1
                  ? 'Unlimited'
                  : `${TIERS.find((t) => t.id === currentTier)?.demos} demos/month`}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {TIERS.map((tier) => (
              <div
                key={tier.id}
                className={`bg-bg-card border rounded-xl p-5 ${
                  tier.id === currentTier
                    ? 'border-primary/40 bg-primary/5'
                    : 'border-border'
                }`}
              >
                <h3 className="font-bold text-lg">{tier.name}</h3>
                <div className="text-2xl font-bold mt-1">
                  {tier.price === 0 ? 'Free' : `€${tier.price}`}
                  {tier.price > 0 && <span className="text-sm text-text-dim font-normal">/mo</span>}
                </div>
                <ul className="mt-3 space-y-1 text-xs text-text-muted">
                  <li>{tier.demos === -1 ? 'Unlimited demos' : `${tier.demos} demos/month`}</li>
                  <li>{tier.seats} {tier.seats === 1 ? 'seat' : 'seats'}</li>
                </ul>
                {tier.id !== currentTier && tier.id !== 'free' && (
                  <button
                    onClick={() => handleUpgrade(tier.id)}
                    className="w-full mt-3 px-3 py-1.5 bg-primary text-white rounded-lg text-xs hover:bg-primary/80"
                  >
                    Upgrade
                  </button>
                )}
                {tier.id === currentTier && (
                  <div className="mt-3 text-xs text-primary font-medium text-center">
                    Current Plan
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="bg-bg-card border border-border rounded-xl p-6">
            <h2 className="text-lg font-bold mb-2 flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              Manage Subscription
            </h2>
            <p className="text-text-dim text-sm mb-3">
              Manage your payment method, invoices, and subscription through Stripe.
            </p>
            <button className="px-4 py-2 bg-bg-elevated border border-border rounded-lg text-sm hover:bg-bg-elevated/80">
              Open Customer Portal
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
