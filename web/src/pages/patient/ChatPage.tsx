import React, { useEffect, useRef, useState } from 'react'
import { Activity, Bot, Plus, Send, User } from 'lucide-react'
import { api } from '../../api/client'
import { DisclaimerBanner } from '../../components/chat/DisclaimerBanner'
import { DoctorRecommendationCard } from '../../components/chat/DoctorRecommendationCard'
import { EmergencyAlert } from '../../components/chat/EmergencyAlert'
import { Alert } from '../../components/common/Alert'
import { LoadingSpinner } from '../../components/common/LoadingSpinner'
import type { ChatMessage, Conversation, DoctorRecommendation } from '../../types'

interface ExtendedChatMessage extends ChatMessage {
  is_emergency?: boolean
  recommendations?: DoctorRecommendation[]
}

export const ChatPage: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ExtendedChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isSending])

  const loadConversations = async () => {
    try {
      setIsLoading(true)
      const list = await api.chat.listConversations()
      setConversations(list)
      if (list.length > 0 && !activeConversationId) {
        selectConversation(list[0].id)
      } else if (list.length === 0) {
        // Automatically start new conversation
        startNewConversation()
      }

    } catch (err: any) {
      console.error('Failed to load conversations:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // Load conversation list
  useEffect(() => {
    loadConversations()
  }, [])

  const selectConversation = async (id: string) => {
    try {
      setActiveConversationId(id)
      setError(null)
      const fullConv = await api.chat.getConversation(id)
      setMessages(fullConv.messages)
    } catch (err: any) {
      setError(err.message || 'Failed to load conversation')
    }
  }

  const startNewConversation = async () => {
    try {
      setIsLoading(true)
      const newConv = await api.chat.createConversation('New Symptom Consultation')
      setConversations((prev) => [newConv, ...prev])
      setActiveConversationId(newConv.id)
      setMessages([
        {
          id: 'welcome',
          conversation_id: newConv.id,
          sender: 'assistant',
          content: newConv.initial_message ?? '',
          created_at: new Date().toISOString(),
        },
      ])
    } catch (err: any) {
      setError(err.message || 'Failed to create new conversation')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputMessage.trim() || !activeConversationId || isSending) return

    const userText = inputMessage.trim()
    setInputMessage('')
    setError(null)

    // Optimistically append user message
    const tempUserMsg: ExtendedChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConversationId,
      sender: 'patient',
      content: userText,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setIsSending(true)

    try {
      const response = await api.chat.sendMessage(activeConversationId, userText)

      const assistantMsg: ExtendedChatMessage = {
        id: `assist-${Date.now()}`,
        conversation_id: activeConversationId,
        sender: 'assistant',
        content: response.assistant_reply,
        created_at: new Date().toISOString(),
        is_emergency: response.is_emergency,
        recommendations: response.recommendations,
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      setError(err.message || 'Failed to receive assistant reply')
    } finally {
      setIsSending(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-65px)] bg-slate-50">
      {/* Permanent Safety Disclaimer */}
      <DisclaimerBanner />

      <div className="flex flex-1 overflow-hidden max-w-7xl w-full mx-auto p-4 gap-4">
        {/* Left Sidebar: Conversations */}
        <aside className="hidden md:flex flex-col w-64 rounded-2xl border border-slate-200 bg-white p-3 shadow-xs">
          <button
            onClick={startNewConversation}
            className="flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-2.5 px-3 text-xs font-bold text-white shadow-xs transition hover:bg-indigo-700 active:scale-95"
          >
            <Plus className="h-4 w-4" />
            New Consultation
          </button>

          <div className="mt-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 px-2">
            Previous Sessions
          </div>

          <div className="mt-2 flex-1 overflow-y-auto space-y-1">
            {conversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => selectConversation(conv.id)}
                className={`w-full text-left rounded-xl p-2.5 text-xs font-medium transition ${
                  conv.id === activeConversationId
                    ? 'bg-indigo-50 text-indigo-700 font-semibold'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                <div className="truncate">{conv.title || 'Symptom Consultation'}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">
                  {new Date(conv.created_at).toLocaleDateString()}
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Right Main: Active Chat Window */}
        <main className="flex flex-1 flex-col rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          {error && (
            <div className="p-3 border-b border-slate-100">
              <Alert type="error" message={error} onClose={() => setError(null)} />
            </div>
          )}

          {/* Messages Scroll Area */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
            {isLoading ? (
              <LoadingSpinner message="Loading consultation..." />
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.sender === 'patient' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.sender === 'assistant' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-xs">
                      <Bot className="h-4 w-4" />
                    </div>
                  )}

                  <div className={`max-w-2xl ${msg.sender === 'patient' ? 'items-end' : 'items-start'}`}>
                    {/* Message Bubble */}
                    <div
                      className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-2xs whitespace-pre-wrap ${
                        msg.sender === 'patient'
                          ? 'bg-indigo-600 text-white rounded-tr-none'
                          : 'border border-slate-200 bg-white text-slate-800 rounded-tl-none'
                      }`}
                    >
                      {msg.content}
                    </div>

                    {/* Emergency Alert (if triggered) */}
                    {msg.is_emergency && <EmergencyAlert message={msg.content} />}

                    {/* Doctor Recommendation Cards Grid (if populated) */}
                    {msg.recommendations && msg.recommendations.length > 0 && (
                      <div className="mt-4 space-y-2">
                        <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-600">
                          <Activity className="h-4 w-4 text-indigo-600" />
                          Recommended Specialists ({msg.recommendations.length})
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                          {msg.recommendations.map((doc) => (
                            <DoctorRecommendationCard key={doc.doctor_id} doctor={doc} />
                          ))}
                        </div>
                      </div>
                    )}

                    <div
                      className={`mt-1 text-[10px] text-slate-400 ${
                        msg.sender === 'patient' ? 'text-right' : 'text-left'
                      }`}
                    >
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>

                  {msg.sender === 'patient' && (
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-700">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))
            )}

            {isSending && (
              <div className="flex items-center gap-2 text-xs text-slate-500 pl-11">
                <div className="h-2 w-2 rounded-full bg-indigo-600 animate-ping" />
                <span>Assistant is evaluating symptoms and specialist availability...</span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <form
            onSubmit={handleSendMessage}
            className="flex items-center gap-2 border-t border-slate-200 bg-slate-50/50 p-3"
          >
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Describe your symptoms (e.g. 'sharp headache for 3 days in Dhaka')..."
              disabled={isSending}
              className="flex-1 rounded-xl border border-slate-200 bg-white py-2.5 px-4 text-sm text-slate-900 transition focus:border-indigo-600 focus:outline-hidden focus:ring-1 focus:ring-indigo-600 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!inputMessage.trim() || isSending}
              className="flex items-center justify-center rounded-xl bg-indigo-600 p-2.5 text-white shadow-xs transition hover:bg-indigo-700 disabled:opacity-40 active:scale-95"
            >
              <Send className="h-5 w-5" />
            </button>
          </form>
        </main>
      </div>
    </div>
  )
}
