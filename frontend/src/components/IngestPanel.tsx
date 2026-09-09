import { useCallback, useRef, useState } from 'react'
import { formatApiError, isApiConfigured } from '../api/client'
import {
  ingestFirImage,
  ingestFirText,
  previewIngest,
  type IngestPreviewResponse,
  type IngestResponse,
} from '../api/ingest'
import { useLanguage } from '../i18n/LanguageContext'

const SAMPLE_FIR = `FIR — suspect Rahul Mukherjee (aka Meera Chopra) called +91 8871205599 from Mumbai.
Transferred INR 2,00,000 from A/C 998877665544 to account 112233445566. Vehicle MH12AB1234 seen near Lokhandwala.`

interface IngestPanelProps {
  caseId: string
  onIngested?: (result: IngestResponse) => void
}

export function IngestPanel({ caseId, onIngested }: IngestPanelProps) {
  const { t } = useLanguage()
  const fileRef = useRef<HTMLInputElement>(null)
  const [text, setText] = useState('')
  const [preview, setPreview] = useState<IngestPreviewResponse | null>(null)
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [loading, setLoading] = useState<'preview' | 'ingest' | 'image' | null>(null)
  const [error, setError] = useState<string | null>(null)

  const runPreview = useCallback(async () => {
    if (!text.trim()) return
    setLoading('preview')
    setError(null)
    setResult(null)
    try {
      const data = await previewIngest(text)
      setPreview(data)
    } catch (err) {
      setPreview(null)
      setError(formatApiError(err, t.ingest.apiError))
    } finally {
      setLoading(null)
    }
  }, [text, t.ingest.apiError])

  const runIngest = useCallback(async () => {
    if (!text.trim()) return
    setLoading('ingest')
    setError(null)
    try {
      const data = await ingestFirText(caseId, text)
      setResult(data)
      setPreview(null)
      onIngested?.(data)
    } catch (err) {
      setError(formatApiError(err, t.ingest.apiError))
    } finally {
      setLoading(null)
    }
  }, [caseId, text, onIngested, t.ingest.apiError])

  const handleImageFile = useCallback(
    async (file: File | null) => {
      if (!file) return
      setLoading('image')
      setError(null)
      setResult(null)
      setPreview(null)
      try {
        const data = await ingestFirImage(caseId, file)
        setResult(data)
        onIngested?.(data)
      } catch (err) {
        setError(formatApiError(err, t.ingest.apiError))
      } finally {
        setLoading(null)
        if (fileRef.current) fileRef.current.value = ''
      }
    },
    [caseId, onIngested, t.ingest.apiError],
  )

  if (!isApiConfigured()) {
    return (
      <section className="border-b border-console-border px-4 py-4">
        <h3 className="text-sm font-semibold text-text-primary">{t.ingest.title}</h3>
        <p className="mt-2 text-sm text-text-muted">{t.ingest.demoOnly}</p>
      </section>
    )
  }

  return (
    <section className="border-b border-console-border px-4 py-4">
      <h3 className="text-sm font-semibold text-text-primary">{t.ingest.title}</h3>
      <p className="mt-1 text-xs leading-relaxed text-text-muted">{t.ingest.subtitle}</p>

      <label className="mt-3 block">
        <span className="text-xs font-medium text-text-primary">{t.ingest.imageLabel}</span>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/jpg"
          disabled={loading !== null}
          onChange={(e) => void handleImageFile(e.target.files?.[0] ?? null)}
          className="mt-1.5 block w-full text-xs text-text-secondary file:mr-2 file:border file:border-console-border-strong file:bg-console-raised file:px-2 file:py-1 file:text-xs"
        />
        <span className="mt-1 block text-[11px] text-text-muted">{t.ingest.imageHint}</span>
        {loading === 'image' && (
          <span className="mt-1 block text-[11px] text-accent-steel">{t.ingest.scanningImage}</span>
        )}
      </label>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={t.ingest.placeholder}
        rows={4}
        className="mt-3 w-full border border-console-border-strong bg-console-bg px-3 py-2 text-sm text-text-primary outline-none focus:border-accent-amber"
      />

      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setText(SAMPLE_FIR)}
          className="min-h-[36px] border border-console-border-strong px-3 py-1.5 text-xs text-text-secondary hover:border-accent-steel"
        >
          {t.ingest.loadSample}
        </button>
        <button
          type="button"
          disabled={loading !== null || !text.trim()}
          onClick={() => void runPreview()}
          className="min-h-[36px] border border-accent-steel/50 px-3 py-1.5 text-xs text-accent-steel hover:bg-accent-steel/10 disabled:opacity-40"
        >
          {loading === 'preview' ? t.ingest.previewing : t.ingest.preview}
        </button>
        <button
          type="button"
          disabled={loading !== null || !text.trim()}
          onClick={() => void runIngest()}
          className="min-h-[36px] border border-accent-amber/50 bg-accent-amber/10 px-3 py-1.5 text-xs text-accent-amber hover:bg-accent-amber/20 disabled:opacity-40"
        >
          {loading === 'ingest' ? t.ingest.ingesting : t.ingest.ingest}
        </button>
      </div>

      {error && (
        <p className="mt-2 border border-risk-high/40 bg-risk-high/10 px-2 py-1.5 text-xs text-risk-high">{error}</p>
      )}

      {preview && (
        <div className="mt-3 border border-console-border bg-console-raised p-3">
          <p className="text-xs text-text-muted">
            {t.ingest.engine}: <span className="text-accent-steel">{preview.engine}</span> ·{' '}
            {preview.entities_extracted} {t.ingest.entities}
          </p>
          <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto text-xs">
            {preview.entities.map((ent) => (
              <li key={`${ent.entity_type}-${ent.text}`} className="text-text-primary">
                <span className="text-accent-amber">{ent.entity_type}</span> — {ent.text}
                <span className="text-text-muted"> ({Math.round(ent.confidence * 100)}%)</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {result && (
        <div className="mt-3 border border-risk-low/40 bg-risk-low/10 p-3 text-xs text-risk-low">
          {t.ingest.success
            .replace('{extracted}', String(result.entities_extracted))
            .replace('{merged}', String(result.entities_merged))}
        </div>
      )}
    </section>
  )
}
