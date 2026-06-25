const STORAGE_KEY = 'vl360_admin_prefs'

interface AdminPrefs {
  sidebarCollapsed: boolean
  pageSize: number
  entityTypeFilter: string
}

const DEFAULTS: AdminPrefs = {
  sidebarCollapsed: false,
  pageSize: 50,
  entityTypeFilter: '',
}

function load(): AdminPrefs {
  if (typeof localStorage === 'undefined') return { ...DEFAULTS }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : { ...DEFAULTS }
  } catch { return { ...DEFAULTS } }
}

function save(prefs: AdminPrefs) {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

const _prefs = ref<AdminPrefs>(DEFAULTS)
let _initialized = false

export function useAdminPrefs() {
  if (!_initialized && import.meta.client) {
    _prefs.value = load()
    _initialized = true
  }

  function setPref<K extends keyof AdminPrefs>(key: K, value: AdminPrefs[K]) {
    _prefs.value[key] = value
    save(_prefs.value)
  }

  return { prefs: _prefs, setPref }
}
