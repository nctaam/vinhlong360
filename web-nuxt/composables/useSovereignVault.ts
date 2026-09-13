/**
 * Sovereign Privacy & Web Crypto API AES-GCM 256-bit Client-Side Vault
 *
 * Implements client-side Zero-Knowledge Sanctum:
 * 1. Web Crypto API (crypto.subtle) AES-GCM 256-bit encryption
 * 2. PBKDF2 key derivation (SHA-256, 100,000 iterations, 16-byte salt)
 * 3. Fresh 12-byte random IV & 128-bit authentication tag per encryption
 * 4. Dual-tier storage: IndexedDB ('vinhlong360_sanctuary_db') with seamless
 *    localStorage fallback ('sovereign_vault_v1')
 * 5. Data portability (exportVaultData) & Right to be Forgotten (purgeVaultData)
 * 6. Conforming to Decree 13/2023/ND-CP and GDPR Art. 25 (Privacy by Design)
 */

import { ref, type Ref } from 'vue'

export type VaultCollection = 'itineraries' | 'private_notes' | 'pocket_pass' | 'favorites' | 'custom'

export interface EncryptedPayload {
  /** Random 12-byte initialization vector (IV), Base64 encoded */
  iv: string
  /** Ciphertext with 128-bit authentication tag appended, Base64 encoded */
  ciphertext: string
  /** Authentication tag length in bits, strictly 128 */
  tagLength: 128
  /** Base64 encoded salt for PBKDF2 */
  salt?: string
  /** Payload schema version */
  version: number
  /** ISO 8601 timestamp */
  updatedAt: string
}

export interface VaultRecord<T = unknown> {
  id: string
  collection: VaultCollection
  payload: EncryptedPayload
  createdAt: string
  updatedAt: string
}

export interface VaultExportArchive {
  schema: 'vinhlong360-sovereign-vault-v1'
  exportedAt: string
  appVersion: string
  vaultMetadata: {
    mode: 'device-bound' | 'passphrase-derived'
    version: number
    totalRecords: number
  }
  records: Array<{
    id: string
    collection: string
    decryptedData: unknown
    updatedAt: string
  }>
}

export type VaultErrorCode =
  | 'VAULT_UNSUPPORTED'
  | 'VAULT_LOCKED'
  | 'INVALID_PASSPHRASE'
  | 'INTEGRITY_COMPROMISED'
  | 'STORAGE_QUOTA_EXCEEDED'
  | 'CORRUPT_PAYLOAD'
  | 'RECORD_NOT_FOUND'

export class SovereignVaultError extends Error {
  public code: VaultErrorCode
  public override cause?: unknown

  constructor(code: VaultErrorCode, message: string, cause?: unknown) {
    super(message)
    this.name = 'SovereignVaultError'
    this.code = code
    this.cause = cause
  }
}

// ── Base64 Encoding / Decoding Helpers (Universal Browser & Node) ──

function bufferToBase64(buffer: Uint8Array): string {
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(buffer).toString('base64')
  }
  let binary = ''
  const len = buffer.byteLength
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(buffer[i]!)
  }
  return btoa(binary)
}

function base64ToBuffer(base64: string): Uint8Array {
  if (typeof Buffer !== 'undefined') {
    return new Uint8Array(Buffer.from(base64, 'base64'))
  }
  const binary = atob(base64)
  const len = binary.length
  const bytes = new Uint8Array(len)
  for (let i = 0; i < len; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes
}

// ── Web Crypto Helpers ──

const STORAGE_KEY = 'sovereign_vault_v1'
const IDB_NAME = 'vinhlong360_sanctuary_db'
const IDB_VERSION = 1
const STORE_RECORDS = 'vault_records'
const STORE_META = 'vault_meta'

// Module-scoped state
let activeKey: CryptoKey | null = null
let currentSalt: string | null = null

const isSupported = ref(false)
const isUnlocked = ref(false)
const vaultMode = ref<'device-bound' | 'passphrase-derived'>('device-bound')
const isBusy = ref(false)

function checkCryptoSupport(): boolean {
  if (typeof window === 'undefined' && typeof globalThis === 'undefined') return false
  const g = typeof window !== 'undefined' ? window : globalThis
  return !!(g.crypto && g.crypto.subtle)
}

// Initialize support status
if (checkCryptoSupport()) {
  isSupported.value = true
}

async function deriveKeyFromPassphrase(
  passphrase: string,
  saltBuffer: Uint8Array,
  iterations = 100_000,
): Promise<CryptoKey> {
  const encoder = new TextEncoder()
  const rawKeyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(passphrase),
    { name: 'PBKDF2' },
    false,
    ['deriveKey'],
  )

  return await crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: saltBuffer as BufferSource,
      iterations,
      hash: 'SHA-256',
    },
    rawKeyMaterial,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

async function generateDeviceBoundKey(): Promise<CryptoKey> {
  return await crypto.subtle.generateKey(
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  )
}

// ── Storage Operations (LocalStorage & IndexedDB Sync) ──

interface LocalVaultStore {
  metadata: {
    version: number
    mode: 'device-bound' | 'passphrase-derived'
    salt?: string
    iterations?: number
    updatedAt: string
  }
  records: Record<string, VaultRecord>
}

function getLocalVaultData(): LocalVaultStore {
  if (typeof localStorage === 'undefined') {
    return {
      metadata: { version: 1, mode: 'device-bound', updatedAt: new Date().toISOString() },
      records: {},
    }
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return {
        metadata: { version: 1, mode: 'device-bound', updatedAt: new Date().toISOString() },
        records: {},
      }
    }
    return JSON.parse(raw) as LocalVaultStore
  } catch {
    return {
      metadata: { version: 1, mode: 'device-bound', updatedAt: new Date().toISOString() },
      records: {},
    }
  }
}

function saveLocalVaultData(store: LocalVaultStore): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch (err) {
    throw new SovereignVaultError('STORAGE_QUOTA_EXCEEDED', 'Bộ nhớ trình duyệt đã đầy hoặc bị hạn chế.', err)
  }
}

// IndexedDB Helper (Progressive Enhancement)
function openIDB(): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    if (typeof indexedDB === 'undefined') {
      resolve(null)
      return
    }
    try {
      const request = indexedDB.open(IDB_NAME, IDB_VERSION)
      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result
        if (!db.objectStoreNames.contains(STORE_RECORDS)) {
          db.createObjectStore(STORE_RECORDS, { keyPath: 'id' })
        }
        if (!db.objectStoreNames.contains(STORE_META)) {
          db.createObjectStore(STORE_META, { keyPath: 'key' })
        }
      }
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => resolve(null)
    } catch {
      resolve(null)
    }
  })
}

async function syncRecordToIDB(record: VaultRecord): Promise<void> {
  const db = await openIDB()
  if (!db) return
  return new Promise((resolve) => {
    try {
      const tx = db.transaction([STORE_RECORDS], 'readwrite')
      const store = tx.objectStore(STORE_RECORDS)
      store.put(record)
      tx.oncomplete = () => resolve()
      tx.onerror = () => resolve()
    } catch {
      resolve()
    }
  })
}

async function removeRecordFromIDB(id: string): Promise<void> {
  const db = await openIDB()
  if (!db) return
  return new Promise((resolve) => {
    try {
      const tx = db.transaction([STORE_RECORDS], 'readwrite')
      const store = tx.objectStore(STORE_RECORDS)
      store.delete(id)
      tx.oncomplete = () => resolve()
      tx.onerror = () => resolve()
    } catch {
      resolve()
    }
  })
}

async function clearIDB(): Promise<void> {
  const db = await openIDB()
  if (!db) return
  return new Promise((resolve) => {
    try {
      const tx = db.transaction([STORE_RECORDS, STORE_META], 'readwrite')
      tx.objectStore(STORE_RECORDS).clear()
      tx.objectStore(STORE_META).clear()
      tx.oncomplete = () => resolve()
      tx.onerror = () => resolve()
    } catch {
      resolve()
    }
  })
}

// ── Composable Definition ──

export function useSovereignVault() {
  if (checkCryptoSupport()) {
    isSupported.value = true
  }

  async function unlockVault(passphrase?: string): Promise<boolean> {
    if (!checkCryptoSupport()) {
      throw new SovereignVaultError('VAULT_UNSUPPORTED', 'Web Crypto API không khả dụng trên môi trường này.')
    }

    isBusy.value = true
    try {
      const store = getLocalVaultData()

      if (passphrase) {
        let saltU8: Uint8Array
        if (store.metadata.salt) {
          saltU8 = base64ToBuffer(store.metadata.salt)
          currentSalt = store.metadata.salt
        } else {
          saltU8 = crypto.getRandomValues(new Uint8Array(16))
          currentSalt = bufferToBase64(saltU8)
          store.metadata.salt = currentSalt
          store.metadata.mode = 'passphrase-derived'
          store.metadata.iterations = 100_000
          saveLocalVaultData(store)
        }

        activeKey = await deriveKeyFromPassphrase(passphrase, saltU8, 100_000)
        vaultMode.value = 'passphrase-derived'
      } else {
        if (!activeKey) {
          activeKey = await generateDeviceBoundKey()
        }
        vaultMode.value = 'device-bound'
      }

      isUnlocked.value = true
      return true
    } finally {
      isBusy.value = false
    }
  }

  function lockVault(): void {
    activeKey = null
    isUnlocked.value = false
  }

  async function ensureActiveKey(): Promise<CryptoKey> {
    if (activeKey) return activeKey
    await unlockVault()
    if (!activeKey) {
      throw new SovereignVaultError('VAULT_LOCKED', 'Khu Bảo Tồn đang bị khóa. Cần mở khóa trước khi thao tác.')
    }
    return activeKey
  }

  async function saveItem<T>(collection: VaultCollection, id: string, data: T): Promise<void> {
    isBusy.value = true
    try {
      const key = await ensureActiveKey()

      // Generate fresh 12-byte random IV for every encryption
      const iv = crypto.getRandomValues(new Uint8Array(12))
      const jsonStr = JSON.stringify(data)
      const encoded = new TextEncoder().encode(jsonStr)

      const encryptedBuffer = await crypto.subtle.encrypt(
        {
          name: 'AES-GCM',
          iv: iv as BufferSource,
          tagLength: 128,
        },
        key,
        encoded as BufferSource,
      )

      const payload: EncryptedPayload = {
        iv: bufferToBase64(iv),
        ciphertext: bufferToBase64(new Uint8Array(encryptedBuffer)),
        tagLength: 128,
        salt: currentSalt || undefined,
        version: 1,
        updatedAt: new Date().toISOString(),
      }

      const store = getLocalVaultData()
      const existing = store.records[id]
      const now = new Date().toISOString()
      const record: VaultRecord = {
        id,
        collection,
        payload,
        createdAt: existing?.createdAt || now,
        updatedAt: now,
      }

      store.records[id] = record
      saveLocalVaultData(store)
      await syncRecordToIDB(record)
    } finally {
      isBusy.value = false
    }
  }

  async function getItem<T>(collection: VaultCollection, id: string): Promise<T | null> {
    isBusy.value = true
    try {
      const store = getLocalVaultData()
      const record = store.records[id]
      if (!record || record.collection !== collection) return null

      const key = await ensureActiveKey()

      try {
        const iv = base64ToBuffer(record.payload.iv)
        const ciphertext = base64ToBuffer(record.payload.ciphertext)

        const decryptedBuffer = await crypto.subtle.decrypt(
          {
            name: 'AES-GCM',
            iv: iv as BufferSource,
            tagLength: 128,
          },
          key,
          ciphertext as BufferSource,
        )

        const jsonStr = new TextDecoder().decode(decryptedBuffer)
        return JSON.parse(jsonStr) as T
      } catch (err) {
        throw new SovereignVaultError(
          'INTEGRITY_COMPROMISED',
          'Xác thực tính toàn vẹn thất bại hoặc khóa không đúng; dữ liệu có thể đã bị giả mạo.',
          err,
        )
      }
    } finally {
      isBusy.value = false
    }
  }

  async function listItems<T>(collection: VaultCollection): Promise<Array<{ id: string; data: T; updatedAt: string }>> {
    const store = getLocalVaultData()
    const records = Object.values(store.records).filter(r => r.collection === collection)
    const results: Array<{ id: string; data: T; updatedAt: string }> = []

    for (const record of records) {
      const data = await getItem<T>(collection, record.id)
      if (data !== null) {
        results.push({ id: record.id, data, updatedAt: record.updatedAt })
      }
    }
    return results
  }

  async function removeItem(collection: VaultCollection, id: string): Promise<boolean> {
    const store = getLocalVaultData()
    if (!store.records[id] || store.records[id].collection !== collection) return false

    delete store.records[id]
    saveLocalVaultData(store)
    await removeRecordFromIDB(id)
    return true
  }

  // ── High-Level Entity Shortcuts ──

  async function saveItinerary(item: { id?: string; [key: string]: any }): Promise<void> {
    const id = item.id || `itin-${Date.now()}`
    await saveItem('itineraries', id, { ...item, id })
  }

  async function getItineraries(): Promise<any[]> {
    const items = await listItems<any>('itineraries')
    return items.map(i => i.data)
  }

  async function savePrivateNote(note: { id?: string; [key: string]: any }): Promise<void> {
    const id = note.id || `note-${Date.now()}`
    await saveItem('private_notes', id, { ...note, id })
  }

  async function getPrivateNotes(): Promise<any[]> {
    const items = await listItems<any>('private_notes')
    return items.map(i => i.data)
  }

  async function savePocketPass(pass: { passId?: string; passCode?: string; [key: string]: any }): Promise<void> {
    const id = pass.passId || pass.passCode || 'pocket-pass-default'
    await saveItem('pocket_pass', id, { ...pass, passId: id })
  }

  async function getPocketPass(): Promise<any | null> {
    const items = await listItems<any>('pocket_pass')
    return items.length > 0 ? (items[0]?.data ?? null) : null
  }

  // ── Data Portability (Export) ──

  async function exportVaultData(): Promise<VaultExportArchive> {
    const store = getLocalVaultData()
    const allRecords = Object.values(store.records)
    const decryptedRecords: VaultExportArchive['records'] = []

    for (const rec of allRecords) {
      const data = await getItem(rec.collection, rec.id)
      decryptedRecords.push({
        id: rec.id,
        collection: rec.collection,
        decryptedData: data,
        updatedAt: rec.updatedAt,
      })
    }

    return {
      schema: 'vinhlong360-sovereign-vault-v1',
      exportedAt: new Date().toISOString(),
      appVersion: '1.0.0',
      vaultMetadata: {
        mode: vaultMode.value,
        version: 1,
        totalRecords: decryptedRecords.length,
      },
      records: decryptedRecords,
    }
  }

  // ── Right to be Forgotten (Purge) ──

  async function purgeVaultData(): Promise<void> {
    isBusy.value = true
    try {
      activeKey = null
      currentSalt = null
      isUnlocked.value = false

      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(STORAGE_KEY)
        // Also clear legacy plain keys if present
        localStorage.removeItem('vl360_plans')
        localStorage.removeItem('vl360_planner_draft')
        localStorage.removeItem('vl360_favorites')
      }

      await clearIDB()

      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('vl360:vault-purged'))
      }
    } finally {
      isBusy.value = false
    }
  }

  return {
    isSupported,
    isUnlocked,
    vaultMode,
    isBusy,
    unlockVault,
    lockVault,
    saveItem,
    getItem,
    listItems,
    removeItem,
    saveItinerary,
    getItineraries,
    savePrivateNote,
    getPrivateNotes,
    savePocketPass,
    getPocketPass,
    exportVaultData,
    purgeVaultData,
  }
}
