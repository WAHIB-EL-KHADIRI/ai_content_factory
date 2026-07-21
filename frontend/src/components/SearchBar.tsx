import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, X, ChevronDown } from 'lucide-react'

export interface FilterOption {
  label: string
  value: string
}

interface SearchBarProps {
  value?: string
  onChange: (value: string) => void
  placeholder?: string
  filters?: {
    key: string
    label: string
    options: FilterOption[]
    value?: string
    onChange?: (value: string) => void
  }[]
}

export default function SearchBar({
  value: controlledValue,
  onChange,
  placeholder = 'Search...',
  filters,
}: SearchBarProps) {
  const [localValue, setLocalValue] = useState(controlledValue ?? '')
  const timerRef = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    if (controlledValue !== undefined) setLocalValue(controlledValue)
  }, [controlledValue])

  const debouncedChange = useCallback(
    (val: string) => {
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => onChange(val), 300)
    },
    [onChange]
  )

  const handleChange = (val: string) => {
    setLocalValue(val)
    debouncedChange(val)
  }

  const handleClear = () => {
    setLocalValue('')
    onChange('')
  }

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
        <input
          type="text"
          value={localValue}
          onChange={e => handleChange(e.target.value)}
          placeholder={placeholder}
          className="input pl-10 pr-10"
        />
        {localValue && (
          <button
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>
      {filters?.map(f => (
        <div key={f.key} className="relative">
          <select
            value={f.value ?? ''}
            onChange={e => f.onChange?.(e.target.value)}
            className="input pr-8 appearance-none cursor-pointer min-w-[140px]"
          >
            <option value="">{f.label}</option>
            {f.options.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={14} />
        </div>
      ))}
    </div>
  )
}
