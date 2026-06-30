import type { Entity } from '~/types'

interface CalendarCell {
  day: number
  isToday?: boolean
  events?: Entity[]
  lunar?: string
  lunarFirst?: boolean
  lunarMid?: boolean
}

export function useEventCalendar(events: Ref<Entity[]>) {
  const today = new Date()
  const calMonth = ref(today.getMonth())
  const calYear = ref(today.getFullYear())

  const displayMonth = computed(() => {
    let m = calMonth.value % 12
    if (m < 0) m += 12
    return m + 1
  })
  const displayYear = computed(() => {
    return calYear.value + Math.floor(calMonth.value / 12)
  })

  watch(calMonth, (v) => {
    if (v < 0) { calYear.value--; calMonth.value = v + 12 }
    else if (v > 11) { calYear.value++; calMonth.value = v - 12 }
  })

  const calendarCells = computed<CalendarCell[]>(() => {
    const y = displayYear.value
    const m = displayMonth.value - 1
    const firstDay = new Date(y, m, 1)
    const lastDay = new Date(y, m + 1, 0)
    const daysInMonth = lastDay.getDate()

    let startDow = firstDay.getDay()
    if (startDow === 0) startDow = 7
    startDow--

    const monthStart = `${y}-${String(m + 1).padStart(2, '0')}-01`
    const monthEnd = `${y}-${String(m + 1).padStart(2, '0')}-${String(daysInMonth).padStart(2, '0')}`
    const dateMap = new Map<number, Entity[]>()
    for (const e of events.value) {
      const attrs = e.attributes || {}
      const ds = attrs.date_start
      const de = attrs.date_end || ds
      if (!ds || de < monthStart || ds > monthEnd) continue
      const span = (new Date(de).getTime() - new Date(ds).getTime()) / 86400000
      if (span > 30) continue
      const from = Math.max(1, ds > monthStart ? parseInt(ds.slice(8), 10) : 1)
      const to = Math.min(daysInMonth, de < monthEnd ? parseInt(de.slice(8), 10) : daysInMonth)
      for (let d = from; d <= to; d++) {
        const arr = dateMap.get(d)
        if (arr) arr.push(e)
        else dateMap.set(d, [e])
      }
    }

    const cells: CalendarCell[] = []
    for (let i = 0; i < startDow; i++) cells.push({ day: 0 })

    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = y === today.getFullYear() && m === today.getMonth() && d === today.getDate()
      const lunar = lunarLabel(d, m + 1, y)
      const lunarFirst = isLunarFirstDay(d, m + 1, y)
      const lunarMid = isLunarFull(d, m + 1, y)
      cells.push({ day: d, isToday, events: dateMap.get(d), lunar, lunarFirst, lunarMid })
    }
    return cells
  })

  return { today, calMonth, calYear, displayMonth, displayYear, calendarCells }
}
