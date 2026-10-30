import React, { createContext, useContext, useEffect, useState } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { api } from '../api/client'
import { supabase } from '../lib/supabase'
import type { UserProfile, UserRole } from '../types'

interface AuthContextType {
  user: User | null
  profile: UserProfile | null
  role: UserRole | null
  session: Session | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  registerPatient: (data: { email: string; password: string; full_name: string; phone?: string }) => Promise<void>
  registerDoctor: (data: { email: string; password: string; full_name: string; phone?: string }) => Promise<void>
  logout: () => Promise<void>
  refreshProfile: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const fetchProfile = async () => {
    try {
      const me = await api.auth.getMe()
      setProfile(me)
    } catch (err) {
      console.error('Failed to fetch user profile:', err)
      setProfile(null)
    }
  }

  useEffect(() => {
    // 1. Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      if (session) {
        fetchProfile().finally(() => setIsLoading(false))
      } else {
        setIsLoading(false)
      }
    })

    // 2. Listen to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (_event, newSession) => {
      setSession(newSession)
      setUser(newSession?.user ?? null)
      if (newSession) {
        await fetchProfile()
      } else {
        setProfile(null)
      }
      setIsLoading(false)
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (error) {
      setIsLoading(false)
      throw new Error(error.message)
    }

    setSession(data.session)
    setUser(data.user)
    await fetchProfile()
    setIsLoading(false)
  }

  const registerPatient = async (data: { email: string; password: string; full_name: string; phone?: string }) => {
    setIsLoading(true)
    try {
      await api.auth.registerPatient(data)
      await login(data.email, data.password)
    } finally {
      setIsLoading(false)
    }
  }

  const registerDoctor = async (data: { email: string; password: string; full_name: string; phone?: string }) => {
    setIsLoading(true)
    try {
      await api.auth.registerDoctor(data)
      await login(data.email, data.password)
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      await supabase.auth.signOut()
      setUser(null)
      setSession(null)
      setProfile(null)
    } finally {
      setIsLoading(false)
    }
  }

  const refreshProfile = async () => {
    await fetchProfile()
  }

  const role: UserRole | null = profile?.role || (user?.user_metadata?.role as UserRole) || null

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
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

