import type { Session, User } from '@supabase/supabase-js'
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, type RegisterInput } from '../api/client'
import { supabase } from '../lib/supabase'
import type { UserProfile, UserRole } from '../types'

interface AuthContextType {
  user: User | null
  profile: UserProfile | null
  role: UserRole | null
  session: Session | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  registerPatient: (data: RegisterInput) => Promise<void>
  registerDoctor: (data: RegisterInput) => Promise<void>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const fetchProfile = useCallback(async () => {
    try {
      setProfile(await api.auth.getMe())
    } catch (err) {
      console.warn('Failed to fetch user profile:', err)
      setProfile(null)
    }
  }, [])

  useEffect(() => {
    let active = true

    void supabase.auth.getSession().then(async ({ data: { session: initial } }) => {
      if (!active) return
      setSession(initial)
      setUser(initial?.user ?? null)
      if (initial) await fetchProfile()
      if (active) setIsLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, next) => {
      setSession(next)
      setUser(next?.user ?? null)
      if (!next) setProfile(null)
      // Awaiting Supabase calls inside this callback deadlocks its auth lock
      else if (event === 'SIGNED_IN') setTimeout(() => void fetchProfile(), 0)
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [fetchProfile])

  const login = useCallback(
    async (email: string, password: string) => {
      const { data, error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw new Error(error.message)
      setSession(data.session)
      setUser(data.user)
      await fetchProfile()
    },
    [fetchProfile]
  )

  const registerPatient = useCallback(
    async (data: RegisterInput) => {
      await api.auth.registerPatient(data)
      await login(data.email, data.password)
    },
    [login]
  )

  const registerDoctor = useCallback(
    async (data: RegisterInput) => {
      await api.auth.registerDoctor(data)
      await login(data.email, data.password)
    },
    [login]
  )

  const logout = useCallback(async () => {
    await supabase.auth.signOut()
    setUser(null)
    setSession(null)
    setProfile(null)
  }, [])

  // The API profile decides the role; user_metadata is editable by the user
  const role: UserRole | null = profile?.role ?? null

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        role,
        session,
        isLoading,
        login,
        registerPatient,
        registerDoctor,
        logout,
        refreshProfile: fetchProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
