import type { ReactNode } from 'react'
import { MastheadHeader } from './MastheadHeader'
import { Tagline } from './Tagline'
import { FooterThesis } from './FooterThesis'
import { ShortcutOverlay } from './ShortcutOverlay'
import { ConnectionMonitor } from './ConnectionMonitor'

/**
 * Page shell. Header / tagline / outlet / footer.
 * Two-column inner layout (content + sidebar) is each Page's responsibility,
 * not the shell's — different pages have different sidebar needs.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <ConnectionMonitor />
      <MastheadHeader />
      <Tagline />
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <FooterThesis />
      <ShortcutOverlay />
    </>
  )
}
