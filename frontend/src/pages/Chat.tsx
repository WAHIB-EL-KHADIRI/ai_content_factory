import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'
import { getErrorMessage } from '../lib/errors'
import { Send, Loader2, Trash2 } from 'lucide-react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  model?: string
  tokens?: number
}

interface ChatUsage {
  output_tokens?: number
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [taskType, setTaskType] = useState('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMsg: Message = { role: 'user', content: input.trim() }
    const allMessages = [...messages, userMsg]
    setMessages(allMessages)
    setInput('')
    setLoading(true)

    try {
      let fullContent = ''
      const assistantMsg: Message = { role: 'assistant', content: '' }
      setMessages([...allMessages, assistantMsg])

      await api.stream('/chat', {
        messages: allMessages.map(m => ({ role: m.role, content: m.content })),
        task_type: taskType,
        stream: true,
        temperature: 0.7,
        max_tokens: 2000,
      }, (chunk) => {
        if (chunk.type === 'delta' && typeof chunk.content === 'string') {
          fullContent += chunk.content
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              role: 'assistant',
              content: fullContent,
              model: chunk.model as string | undefined,
            }
            return updated
          })
        }
        if (chunk.type === 'done') {
          setMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = {
              role: 'assistant',
              content: chunk.content as string,
              model: chunk.model as string,
              tokens: (chunk.usage as ChatUsage | undefined)?.output_tokens,
            }
            return updated
          })
        }
      })
    } catch (err) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Error: ${getErrorMessage(err)}`,
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">AI Chat</h1>
          <p className="text-gray-400 mt-1">Multi-model AI assistant with streaming</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={taskType}
            onChange={e => setTaskType(e.target.value)}
            className="input w-auto"
          >
            <option value="chat">Chat</option>
            <option value="content_writing">Writing</option>
            <option value="seo_analysis">SEO</option>
            <option value="editing">Editing</option>
            <option value="translation">Translation</option>
            <option value="summarization">Summarization</option>
          </select>
          <button onClick={() => setMessages([])} className="btn-secondary flex items-center gap-2" disabled={messages.length === 0}>
            <Trash2 size={16} /> Clear
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-1">Choose a task type and type your message</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-brand-600 text-white'
                : 'bg-gray-800 text-gray-100'
            }`}>
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {msg.model && (
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-400">
                  <span>{msg.model}</span>
                  {msg.tokens && <span>&middot; {msg.tokens} tokens</span>}
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="flex items-end gap-3 border-t border-gray-800 pt-4">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className="input resize-none min-h-[44px] max-h-32"
          rows={1}
          disabled={loading}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="btn-primary px-4 py-3 flex-shrink-0"
        >
          {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
        </button>
      </div>
    </div>
  )
}
