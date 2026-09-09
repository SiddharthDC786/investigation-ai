/** Clean internal case IDs and demo dataset wording for the investigator UI. */
export function displayCaseTitle(raw: string): string {
  return raw
    .replace(/^Synthetic\s+/i, '')
    .replace(/\s*Ring\s*\d*\s*/gi, ' ')
    .replace(/\s*—\s*—/g, ' —')
    .replace(/\s+/g, ' ')
    .trim()
}

export function displayCaseRef(_caseId: string, displayRef = 'FIR-042/2026'): string {
  return displayRef
}
