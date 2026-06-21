import { useLayoutEffect, useRef, useState } from 'react'

type NavigationItem<ItemId extends string> = {
  id: ItemId
  label: string
}

type PrimaryNavProps<ItemId extends string> = {
  activeId: ItemId | null
  items: Array<NavigationItem<ItemId>>
  onChange: (id: ItemId) => void
}

type SliderMetrics = {
  width: number
  x: number
  visible: boolean
}

export default function PrimaryNav<ItemId extends string>({ activeId, items, onChange }: PrimaryNavProps<ItemId>) {
  const navRef = useRef<HTMLElement>(null)
  const buttonRefs = useRef(new Map<ItemId, HTMLButtonElement>())
  const [slider, setSlider] = useState<SliderMetrics>({ width: 0, x: 0, visible: false })

  useLayoutEffect(() => {
    const nav = navRef.current
    if (!nav) return

    function updateSlider() {
      const activeButton = activeId ? buttonRefs.current.get(activeId) : undefined
      if (!activeButton) {
        setSlider((current) => ({ ...current, visible: false }))
        return
      }

      setSlider({ width: activeButton.offsetWidth, x: activeButton.offsetLeft, visible: true })
    }

    updateSlider()

    const observer = new ResizeObserver(updateSlider)
    observer.observe(nav)
    buttonRefs.current.forEach((button) => observer.observe(button))

    return () => observer.disconnect()
  }, [activeId, items])

  return (
    <nav ref={navRef} aria-label="顶部导航" className="relative hidden items-center rounded-xl bg-slate-100 p-1 md:flex">
      <span
        aria-hidden="true"
        className="pointer-events-none absolute bottom-1 left-0 top-1 rounded-lg bg-white shadow-sm transition-[width,transform,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
        style={{
          opacity: slider.visible ? 1 : 0,
          transform: `translateX(${slider.x}px)`,
          width: slider.width,
        }}
      />

      {items.map((item) => {
        const active = item.id === activeId

        return (
          <button
            key={item.id}
            ref={(element) => {
              if (element) buttonRefs.current.set(item.id, element)
              else buttonRefs.current.delete(item.id)
            }}
            aria-current={active ? 'page' : undefined}
            className={`relative z-10 rounded-lg px-4 py-1.5 text-sm transition-[color,transform] duration-200 ${
              active ? 'font-semibold text-slate-950' : 'font-medium text-slate-500 hover:text-slate-900 active:scale-[0.97]'
            }`}
            onClick={() => onChange(item.id)}
            type="button"
          >
            {item.label}
          </button>
        )
      })}
    </nav>
  )
}
