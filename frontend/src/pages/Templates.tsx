import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../hooks/useToast'
import { api } from '../api/client'
import {
  FileText, Share2, Mail, Video, Megaphone, BookOpen,
  Newspaper, MessageCircle, ArrowRight,
} from 'lucide-react'

interface Template {
  id: string
  name: string
  description: string
  icon: typeof FileText
  contentType: string
  color: string
}

const templates: Template[] = [
  {
    id: 'blog-post',
    name: 'Blog Post',
    description: 'SEO-optimized long-form blog articles with proper structure and headings.',
    icon: FileText,
    contentType: 'blog_post',
    color: 'bg-blue-600/20 text-blue-400 border-blue-800',
  },
  {
    id: 'social-media',
    name: 'Social Media Post',
    description: 'Engaging social media content for Twitter, LinkedIn, and Instagram.',
    icon: Share2,
    contentType: 'social_media',
    color: 'bg-purple-600/20 text-purple-400 border-purple-800',
  },
  {
    id: 'newsletter',
    name: 'Newsletter',
    description: 'Professional email newsletters with compelling subject lines.',
    icon: Mail,
    contentType: 'newsletter',
    color: 'bg-green-600/20 text-green-400 border-green-800',
  },
  {
    id: 'video-script',
    name: 'Video Script',
    description: 'Structured scripts for YouTube, TikTok, or product demos.',
    icon: Video,
    contentType: 'video_script',
    color: 'bg-red-600/20 text-red-400 border-red-800',
  },
  {
    id: 'ad-copy',
    name: 'Ad Copy',
    description: 'High-converting ad copy for Google Ads, Facebook, and more.',
    icon: Megaphone,
    contentType: 'ad_copy',
    color: 'bg-yellow-600/20 text-yellow-400 border-yellow-800',
  },
  {
    id: 'product-description',
    name: 'Product Description',
    description: 'Compelling product descriptions that drive conversions.',
    icon: BookOpen,
    contentType: 'product_description',
    color: 'bg-orange-600/20 text-orange-400 border-orange-800',
  },
  {
    id: 'press-release',
    name: 'Press Release',
    description: 'Professional press releases following industry standards.',
    icon: Newspaper,
    contentType: 'press_release',
    color: 'bg-indigo-600/20 text-indigo-400 border-indigo-800',
  },
  {
    id: 'chatbot-response',
    name: 'Chatbot Response',
    description: 'Natural conversational responses for AI chatbots.',
    icon: MessageCircle,
    contentType: 'chatbot_response',
    color: 'bg-teal-600/20 text-teal-400 border-teal-800',
  },
]

export default function Templates() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [creating, setCreating] = useState(false)

  const handleCreate = async (template: Template) => {
    setCreating(true)
    try {
      const res = await api.post<{ id: string }>('/content', {
        title: `New ${template.name}`,
        content_type: template.contentType,
        content: '',
        status: 'draft',
      })
      toast.success(`${template.name} template created`)
      navigate(`/content?id=${res.id}`)
    } catch {
      toast.error('Failed to create from template')
    } finally {
      setCreating(false)
      setSelectedTemplate(null)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Templates</h1>
        <p className="text-gray-400 mt-1">Start with a pre-built content template</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {templates.map(template => {
          const Icon = template.icon
          return (
            <button
              key={template.id}
              type="button"
              className="card group cursor-pointer hover:border-gray-700 transition-all duration-200 w-full text-left"
              onClick={() => setSelectedTemplate(template)}
            >
              <div className={`inline-flex p-3 rounded-xl border ${template.color} mb-4`}>
                <Icon size={24} />
              </div>
              <h3 className="text-lg font-semibold text-gray-100 mb-2">{template.name}</h3>
              <p className="text-sm text-gray-400 leading-relaxed mb-4">{template.description}</p>
              <div className="flex items-center gap-1 text-sm font-medium text-brand-400 group-hover:text-brand-300 transition-colors">
                Use template <ArrowRight size={14} />
              </div>
            </button>
          )
        })}
      </div>

      {selectedTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="card w-full max-w-md mx-4 space-y-5">
            <h2 className="text-xl font-semibold">Create from Template</h2>
            <p className="text-gray-400">
              This will create a new draft content item from the <strong>{selectedTemplate.name}</strong> template.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setSelectedTemplate(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => handleCreate(selectedTemplate)}
                disabled={creating}
                className="btn-primary"
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
