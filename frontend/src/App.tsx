
import React, { useEffect, useMemo, useRef, useState } from 'react'
import { DataSet } from 'vis-data'
import { Timeline } from 'vis-timeline/standalone'
import 'vis-timeline/styles/vis-timeline-graph2d.min.css'
import { fetchWorkOrders, updateOperation } from './api'
import type { WorkOrder, Operation } from './types'

// Helpers
function isoToDate(iso: string) { return new Date(iso) }
function dateToIso(d: Date) { return d.toISOString() }

export default function App() {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const timelineRef = useRef<Timeline | null>(null)

  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([])
  const [selectedWO, setSelectedWO] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load data
  useEffect(() => {
    fetchWorkOrders().then(setWorkOrders).catch(e => setError(String(e)))
  }, [])

  // Build groups (lanes) and items for vis-timeline
  const { groups, items } = useMemo(() => {
    const machineIds = Array.from(new Set(workOrders.flatMap(wo => wo.operations.map(o => o.machineId)))).sort()
    const groups = machineIds.map(id => ({ id, content: id }))
    const items = workOrders.flatMap(wo => wo.operations.map(op => ({
      id: op.id,
      group: op.machineId,
      start: op.start,
      end: op.end,
      content: `${wo.id} · ${op.name}`,
      workOrderId: wo.id
    })))
    return { groups, items }
  }, [workOrders])

  // Draw timeline
  useEffect(() => {
    if (!containerRef.current) return
    const groupsDS = new DataSet(groups as any)
    const itemsDS = new DataSet(items as any)

    const timeline = new Timeline(containerRef.current, itemsDS, groupsDS, {
      stack: false,
      showCurrentTime: true,
      orientation: 'top',
      margin: { item: 8, axis: 16 },
      zoomMin: 1000 * 60 * 5,  // 5 minutes
      zoomMax: 1000 * 60 * 60 * 24 * 7,
      multiselect: false,
      selectable: true
    })
    timelineRef.current = timeline

    timeline.on('select', (props: any) => {
      const id = props.items[0]
      if (!id) { setSelectedWO(null); return }
      const op = items.find(i => i.id === id)
      setSelectedWO(op?.workOrderId ?? null)
    })

    // clicking on empty space doesn't trigger "select", so add DOM handler to clear
    function handleClickBlank(ev: MouseEvent) {
      const target = ev.target as HTMLElement
      // if clicked on background (not on an item)
      if (target.closest('.vis-item')) return
      setSelectedWO(null)
    }
    const cont = containerRef.current
    cont.addEventListener('click', handleClickBlank)

    return () => {
      cont.removeEventListener('click', handleClickBlank)
      timeline.destroy()
    }
  }, [groups, items])

  // Highlight same WO via DOM class toggling
  useEffect(() => {
    const root = containerRef.current
    if (!root) return
    root.querySelectorAll('.vis-item').forEach(el => {
      const title = (el as HTMLElement).innerText || ''
      const woId = title.split(' · ')[0]
      if (selectedWO && woId === selectedWO) {
        el.classList.add('highlight-wo')
      } else {
        el.classList.remove('highlight-wo')
      }
    })
  }, [selectedWO, items])

  async function nudge(op: Operation, minutesDelta: number) {
    setError(null)
    const newStart = new Date(isoToDate(op.start).getTime() + minutesDelta * 60_000)
    const newEnd = new Date(isoToDate(op.end).getTime() + minutesDelta * 60_000)
    try {
      const updated = await updateOperation(op.id, dateToIso(newStart), dateToIso(newEnd))
      // refresh
      const fresh = await fetchWorkOrders()
      setWorkOrders(fresh)
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? String(e))
    }
  }

  return (
    <div style={{ fontFamily: 'Inter, system-ui, sans-serif', padding: 16 }}>
      <h1>Factory Scheduler</h1>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
        <button onClick={() => setSelectedWO(null)}>Clear highlight</button>
        {selectedWO && <span>Highlighted: <b>{selectedWO}</b></span>}
        {error && <span style={{ color: 'crimson' }}>Error: {error}</span>}
      </div>
      <div ref={containerRef} style={{ height: '60vh', border: '1px solid #ddd', borderRadius: 8 }} />
      <p style={{ marginTop: 12 }}>
        Tip: Bir operasyonu test için <i>±10 dk kaydır</i> (API validasyonlarını görmek için).
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8 }}>
        {workOrders.flatMap(wo => wo.operations).map(op => (
          <div key={op.id} style={{ border: '1px solid #eee', padding: 8, borderRadius: 8 }}>
            <div><b>{op.id}</b> — {op.name} ({op.machineId})</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>{op.start} → {op.end}</div>
            <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
              <button onClick={() => nudge(op, -10)}>-10 dk</button>
              <button onClick={() => nudge(op, 10)}>+10 dk</button>
            </div>
          </div>
        ))}
      </div>

      <style>
        {`.highlight-wo { outline: 3px solid #1e90ff; background: rgba(30,144,255,0.15) !important; }`}
      </style>
    </div>
  )
}
