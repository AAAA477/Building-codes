import type { ReactNode } from 'react'

export type Hue = 'orange' | 'yellow' | 'grass' | 'teal' | 'ultra' | 'violet'
export interface TabDef { key: string; n: string; label: string; hue: Hue; open: number; current: boolean; disabled?: boolean; onClick: () => void }

/** Tab height grows with the work still open on that tab (clamped). */
const heightFor = (open: number) => Math.min(168, 84 + open * 9)

export function Rail({ tabs, label }: { tabs: TabDef[]; label: string }) {
  return (
    <nav className="rail" aria-label={label}>
      <ol>
        {tabs.map(t => (
          <li key={t.key}>
            <button type="button" className={`tab tab-${t.hue}`} style={{ height: heightFor(t.open) }} disabled={t.disabled}
              aria-current={t.current ? 'step' : undefined} onClick={t.onClick}
              title={t.disabled ? 'Locked until you describe your project' : undefined}
              aria-label={`${t.label}, ${t.open ? t.open + ' open' : 'nothing open'}${t.disabled ? ', locked' : ''}`}>
              <span className="tn">{t.n}</span>
              <span className="tl">{t.label}</span>
              <span className="to">{t.open ? <><b>{t.open}</b> open</> : 'clear'}</span>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

/** Board strip + leaf the content sits on. */
export function Binder({ hue, tabs, railLabel, strip, wide, children }: { hue: Hue; tabs: TabDef[]; railLabel: string; strip?: ReactNode; wide?: boolean; children: ReactNode }) {
  return (
    <div className="binder">
      <Rail tabs={tabs} label={railLabel} />
      <div className={`board hue-${hue}`}>
        <div className="stripline">{strip}</div>
        <div className={`leaf ${wide ? 'wide' : ''}`}>{children}</div>
      </div>
    </div>
  )
}
