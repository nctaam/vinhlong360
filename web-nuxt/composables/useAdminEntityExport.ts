import type { Ref } from 'vue'
import type { Entity } from '~/types'

export function useAdminEntityExport(
  entities: Ref<Entity[]>,
  downloader: (blob: Blob, filename: string) => void = downloadBlob,
) {
  function exportJSON() {
    downloader(
      new Blob([JSON.stringify(entities.value, null, 2)], { type: 'application/json' }),
      'entities-' + new Date().toISOString().slice(0, 10) + '.json',
    )
  }

  function exportCSV() {
    const cols = ['id', 'name', 'type', 'placeId', 'summary']
    const esc = (v: unknown) => '"' + String(v ?? '').replace(/"/g, '""') + '"'
    const rows = entities.value.map(e => cols.map(c => esc((e as Record<string, any>)[c])).join(','))
    const csv = '\uFEFF' + cols.join(',') + '\n' + rows.join('\n')
    downloader(
      new Blob([csv], { type: 'text/csv;charset=utf-8' }),
      'entities-' + new Date().toISOString().slice(0, 10) + '.csv',
    )
  }

  return {
    exportJSON,
    exportCSV,
  }
}
