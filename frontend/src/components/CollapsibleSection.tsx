import { useState, type ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: ReactNode
}

export function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
}: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className="border-b border-console-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-console-raised/50"
      >
        <div>
          <h3 className="text-xs font-semibold text-text-primary">{title}</h3>
          {subtitle && <p className="mt-0.5 text-[11px] text-text-muted">{subtitle}</p>}
        </div>
        <span className="shrink-0 text-sm text-accent-steel">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </section>
  )
}
