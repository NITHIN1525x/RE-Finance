// The generated files in <repo>/submission/ are the ONLY source for the Results page.
// Vite inlines them into the bundle at build time (?raw), so nothing is fetched at run time and no API is called.
// To change what is shown, regenerate the files (python scripts/build_submission.py) and rebuild.
const files = import.meta.glob('../../../../submission/*.md', { query: '?raw', import: 'default', eager: true })

export const SUBMISSION = Object.fromEntries(
  Object.entries(files).map(([path, text]) => [decodeURIComponent(path.split('/').pop()), text]),
)

// PDFs in submission/ are bundled as downloadable assets (URL only; nothing is parsed or executed).
const pdfs = import.meta.glob('../../../../submission/*.pdf', { query: '?url', import: 'default', eager: true })

export const SUBMISSION_PDFS = Object.fromEntries(
  Object.entries(pdfs).map(([path, url]) => [decodeURIComponent(path.split('/').pop()), url]),
)
