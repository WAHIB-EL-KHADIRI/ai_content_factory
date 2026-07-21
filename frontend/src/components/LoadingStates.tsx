import { Loader2 } from 'lucide-react'

export function Spinner({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <div className={`flex items-center justify-center py-12 ${className}`}>
      <Loader2 className="animate-spin text-brand-500" size={size} />
    </div>
  )
}
