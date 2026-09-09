import { apiPost, getApiBase, isApiConfigured } from './client'

export interface IngestMention {
  text: string
  entity_type: string
  resolved_entity_id?: string | null
  action: string
  source_excerpt?: string | null
}

export interface IngestResponse {
  status: string
  source_id: string
  source_type: string
  case_id?: string | null
  records_received: number
  entities_extracted: number
  entities_merged: number
  mentions: IngestMention[]
  extracted_text?: string | null
}

export interface PreviewEntity {
  text: string
  entity_type: string
  confidence: number
  source_excerpt?: string | null
}

export interface IngestPreviewResponse {
  engine: string
  spacy_available: boolean
  entities_extracted: number
  entities: PreviewEntity[]
}

export async function previewIngest(text: string): Promise<IngestPreviewResponse> {
  return apiPost<IngestPreviewResponse>('/ingest/preview', { text })
}

export async function ingestFirText(caseId: string, text: string): Promise<IngestResponse> {
  const body = new FormData()
  body.append('text', text)
  body.append('case_id', caseId)

  const res = await fetch(`${getApiBase()}/ingest/fir/text`, {
    method: 'POST',
    body,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText)
    throw new Error(`Ingest failed: ${msg}`)
  }
  return res.json() as Promise<IngestResponse>
}

export async function ingestFirImage(caseId: string, file: File): Promise<IngestResponse> {
  const body = new FormData()
  body.append('file', file)
  body.append('case_id', caseId)

  const res = await fetch(`${getApiBase()}/ingest/fir/image`, {
    method: 'POST',
    body,
  })
  if (!res.ok) {
    const msg = await res.text().catch(() => res.statusText)
    throw new Error(`Image ingest failed: ${msg}`)
  }
  return res.json() as Promise<IngestResponse>
}

export function isIngestLive(): boolean {
  return isApiConfigured()
}
