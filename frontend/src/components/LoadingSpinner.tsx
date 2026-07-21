import { Loader2 } from 'lucide-react'

export default function LoadingSpinner({ text }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3">
      <Loader2 className="animate-spin text-brand-500" size={32} />
      {text && <p className="text-sm text-gray-400">{text}</p>}
    </div>
  )
}
