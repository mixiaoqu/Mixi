import type { ReactNode } from 'react'

export type IconName =
  | 'spark'
  | 'search'
  | 'play'
  | 'check'
  | 'loader'
  | 'database'
  | 'terminal'
  | 'wand'
  | 'book'
  | 'grid'
  | 'back'
  | 'arrow'
  | 'bolt'
  | 'globe'
  | 'megaphone'
  | 'upload'
  | 'sync'
  | 'trash'
  | 'plus'
  | 'users'
  | 'file'
  | 'copy'
  | 'refresh'
  | 'eye'
  | 'eye-off'
  | 'mail'
  | 'lock'

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  const common = {
    className,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    'aria-hidden': true,
  }

  const paths: Record<IconName, ReactNode> = {
    spark: <><path d="m12 3 1.7 5.2L19 10l-5.3 1.8L12 17l-1.7-5.2L5 10l5.3-1.8Z" /><path d="M5 3v4" /><path d="M3 5h4" /><path d="M19 17v4" /><path d="M17 19h4" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
    play: <path d="m8 5 11 7-11 7Z" />,
    check: <><path d="M20 6 9 17l-5-5" /><circle cx="12" cy="12" r="10" /></>,
    loader: <><path d="M21 12a9 9 0 1 1-6.2-8.6" /><path d="M21 3v6h-6" /></>,
    database: <><ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5" /><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6" /></>,
    terminal: <><path d="m4 17 5-5-5-5" /><path d="M12 19h8" /></>,
    wand: <><path d="M15 4V2" /><path d="M15 16v-2" /><path d="M8 9h2" /><path d="M20 9h2" /><path d="m17.8 6.2 1.4-1.4" /><path d="m10.8 13.2-1.4 1.4" /><path d="m17.8 11.8 1.4 1.4" /><path d="m3 21 9.5-9.5" /></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M4 4v15.5" /><path d="M20 4v13" /><path d="M6.5 4H20" /><path d="M6.5 17H20" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
    back: <><path d="m15 18-6-6 6-6" /></>,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    bolt: <path d="m13 2-9 13h8l-1 7 9-13h-8Z" />,
    globe: <><circle cx="12" cy="12" r="10" /><path d="M2 12h20" /><path d="M12 2a15 15 0 0 1 0 20" /><path d="M12 2a15 15 0 0 0 0 20" /></>,
    megaphone: <><path d="m3 11 18-5v12L3 13Z" /><path d="M7 14v5a2 2 0 0 0 2 2h1" /></>,
    upload: <><path d="M12 16V4" /><path d="m7 9 5-5 5 5" /><path d="M20 16.5A4.5 4.5 0 0 1 15.5 21h-7A4.5 4.5 0 0 1 4 16.5" /></>,
    sync: <><path d="M21 12a9 9 0 0 1-14.9 6.8" /><path d="M3 12A9 9 0 0 1 17.9 5.2" /><path d="M17 2v4h4" /><path d="M7 22v-4H3" /></>,
    trash: <><path d="M3 6h18" /><path d="M8 6V4h8v2" /><path d="M6 6l1 15h10l1-15" /><path d="M10 11v6" /><path d="M14 11v6" /></>,
    plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.9" /><path d="M16 3.1a4 4 0 0 1 0 7.8" /></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" /><path d="M14 2v6h6" /><path d="M8 13h8" /><path d="M8 17h5" /></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M4 16V6a2 2 0 0 1 2-2h10" /></>,
    refresh: <><path d="M21 12a9 9 0 0 1-9 9 8.6 8.6 0 0 1-6-2.4" /><path d="M3 12a9 9 0 0 1 15-6.7" /><path d="M18 3v5h-5" /><path d="M6 21v-5h5" /></>,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
    'eye-off': <><path d="m3 3 18 18" /><path d="M10.6 10.6A2 2 0 0 0 12 14a2 2 0 0 0 1.4-.6" /><path d="M9.9 5.2A9.8 9.8 0 0 1 12 5c6.5 0 10 7 10 7a18 18 0 0 1-2.1 3.1" /><path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.5 7 10 7a9.7 9.7 0 0 0 4.2-.9" /></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>,
    lock: <><rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></>,
  }

  return <svg {...common}>{paths[name]}</svg>
}
