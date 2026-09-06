import type { HomePresentationEntity } from '~/utils/homeNocturnePresentation'
import { resolveFreshnessStatus, resolveSourceTier } from '~/utils/regionalColor'


export function formatFreshnessLabel(value?: string | null): string {
  if (!value || !Number.isFinite(Date.parse(value))) return ''
  return `Cập nhật ${new Intl.DateTimeFormat('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(value))}`
}

export function metadataRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? value as Record<string, unknown> : {}
}

export function metadataText(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

export function eventMetadata(event: HomePresentationEntity) {
  return {
    source: metadataRecord(event?.source_freshness),
    quality: metadataRecord(event?.quality),
  }
}

export function eventSourceTier(event: HomePresentationEntity) {
  const { source, quality } = eventMetadata(event)
  return resolveSourceTier(source.source_tier || quality.source_tier)
}

export function eventSourceTitle(event: HomePresentationEntity): string {
  const { source, quality } = eventMetadata(event)
  return metadataText(source.source_title) || metadataText(quality.source_title)
}

export function eventSourceUrl(event: HomePresentationEntity): string {
  const { source, quality } = eventMetadata(event)
  return metadataText(source.source_url) || metadataText(quality.source_url)
}

export function eventVerifiedAt(event: HomePresentationEntity): string {
  const { source, quality } = eventMetadata(event)
  return metadataText(source.verified_at) || metadataText(quality.verified_at)
}

export function eventFreshnessStatus(event: HomePresentationEntity) {
  return resolveFreshnessStatus(eventMetadata(event).source.freshness_status)
}

export function eventFreshnessLabel(event: HomePresentationEntity): string {
  const sourceUpdatedAt = metadataText(eventMetadata(event).source.updated_at)
  const entityUpdatedAt = metadataText(event?.updatedAt)
  return formatFreshnessLabel(sourceUpdatedAt || entityUpdatedAt)
}
