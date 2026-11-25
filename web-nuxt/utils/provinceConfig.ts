import rawProvinceConfig from '../../config/province.config.json'

export interface ProvinceIdentityConfig {
  readonly slug: string
  readonly provinceSlug: string
  readonly provinceId: string
  readonly provinceName: string
  readonly provinceFullName: string
  readonly brandName: string
  readonly brandDisplayName: string
  readonly logoSuffix: string
  readonly domain: string
  readonly siteUrl: string
  readonly contactEmail: string
  readonly zaloHandle: string
  readonly twitterHandle: string
  readonly esmsBrandname: string
  readonly storagePrefix: string
  readonly weatherUserAgent: string
  readonly ogImagePath: string
  readonly tagline: string
  readonly footerTagline: string
  readonly copyright: string
  readonly alternateName: string
  readonly seoTitle: string
  readonly seoDescription: string
  readonly ogDescription: string
  readonly jsonLdDescription: string
  readonly seedSeoDescription: string
  readonly heroSubtitle: string
  readonly chatTitle: string
  readonly chatPlaceholder: string
  readonly wardCount: number
  readonly mergedDate: string
  readonly mergedFrom: readonly string[]
  readonly legacyProvinceNames: readonly string[]
  readonly terroirBasin: string
  readonly knowsAbout: readonly string[]
}

export interface ProvinceBboxRange {
  readonly lat: readonly [number, number]
  readonly lng: readonly [number, number]
}

export interface ProvinceBoundsConfig {
  readonly schemaBbox: ProvinceBboxRange
  readonly ingestBbox: ProvinceBboxRange
  readonly spatialBox: string
}

export interface ProvinceAreaConfig {
  readonly slug: string
  readonly name: string
  readonly emoji: string
  readonly icon: string
  readonly blurb: string
  readonly distance: string
  readonly hub: string
  readonly lat: number
  readonly lon: number
  readonly isPrimary: boolean
}

export interface ProvinceMultiRegionMetaConfig {
  readonly slug: string
  readonly name: string
  readonly emoji: string
  readonly icon: string
  readonly blurb: string
  readonly distance: string
  readonly hub: string
}

export interface ProvinceAreasConfig {
  readonly canonicalAreaSlug: string
  readonly canonicalRegionId: string
  readonly legacyRegionIds: readonly string[]
  readonly legacyRegionLabels: readonly string[]
  readonly currentProvinceAliases: readonly string[]
  readonly multiRegionSlug: string
  readonly multiRegionLabel: string
  readonly items: readonly ProvinceAreaConfig[]
  readonly multiRegionMeta: ProvinceMultiRegionMetaConfig
}

export interface ProvinceWeatherMeasurePoint {
  readonly area: string
  readonly label: string
  readonly coordinates: readonly [number, number]
  readonly asyncDataKey: string
}

export interface ProvinceWeatherConfig {
  readonly measurePoint: ProvinceWeatherMeasurePoint
  readonly rainySeasonMonths: readonly number[]
  readonly rainyClimateContext: string
  readonly dryClimateContext: string
}

export interface ProvinceTideConfig {
  readonly riverAzimuthSeaward: number
  readonly riverAzimuthLandward: number
  readonly meanStageMeters: number
  readonly tau1Hours: number
  readonly tau2Hours: number
  readonly floodFlowDesc: string
  readonly ebbFlowDesc: string
  readonly folkWisdom: string
}

export interface ProvinceEmergencyHotline {
  readonly id: string
  readonly name: string
  readonly phone: string
  readonly tel_uri: string
  readonly service_scope: string
  readonly badge: string
  readonly priority: boolean
}

export interface ProvinceContentGuardsConfig {
  readonly outOfProvincePatterns: readonly string[]
  readonly outOfProvinceMessage: string
}

export interface ProvinceCuratedLead {
  readonly id: string
  readonly title: string
  readonly location: string
  readonly desc: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
}

export interface ProvinceCuratedSatellite {
  readonly id: string
  readonly title: string
  readonly area: string
  readonly summary: string
  readonly coverSrc: string
  readonly to: string
}

export interface ProvinceCulinaryDish {
  readonly id: string
  readonly name: string
  readonly origin: string
  readonly reputableVenue: string
  readonly priceRange: string
  readonly coverSrc: string
  readonly to: string
  readonly mapTo: string
}

export interface ProvinceCuratedHomestay {
  readonly id: string
  readonly name: string
  readonly price: string
  readonly area: string
  readonly desc: string
  readonly coverSrc: string
  readonly to: string
}

export interface ProvinceHomeConfig {
  readonly curatedShowcase: {
    readonly ariaLabel: string
    readonly eyebrow: string
    readonly title: string
    readonly subtitle: string
    readonly seeAllLabel: string
    readonly fallbackImage: string
    readonly lead: ProvinceCuratedLead
    readonly satellites: readonly ProvinceCuratedSatellite[]
  }
  readonly culinaryTrail: {
    readonly ariaLabel: string
    readonly eyebrow: string
    readonly title: string
    readonly subtitle: string
    readonly seeAllLabel: string
    readonly fallbackImage: string
    readonly dishes: readonly ProvinceCulinaryDish[]
  }
  readonly riversideStays: {
    readonly ariaLabel: string
    readonly eyebrow: string
    readonly title: string
    readonly subtitle: string
    readonly seeAllLabel: string
    readonly fallbackImage: string
    readonly stays: readonly ProvinceCuratedHomestay[]
  }
}

export interface ProvinceDeployConfig {
  readonly appDir: string
  readonly dbFilename: string
  readonly agentService: string
  readonly webService: string
  readonly botService: string
  readonly agentPort: number
  readonly webPort: number
  readonly defaultSshKey: string
}

export interface ProvinceConfig {
  readonly schemaVersion: 1
  readonly identity: ProvinceIdentityConfig
  readonly bounds: ProvinceBoundsConfig
  readonly areas: ProvinceAreasConfig
  readonly weather: ProvinceWeatherConfig
  readonly tide: ProvinceTideConfig
  readonly emergencyHotlines: readonly ProvinceEmergencyHotline[]
  readonly contentGuards: ProvinceContentGuardsConfig
  readonly home: ProvinceHomeConfig
  readonly deploy: ProvinceDeployConfig
}

export interface AreaMetaEntry {
  name: string
  emoji: string
  icon: string
  blurb: string
  distance?: string
  hub?: string
}

function isObjectRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function requireText(record: Record<string, unknown>, key: string, ctx: string): string {
  const val = record[key]
  if (typeof val !== 'string' || !val.trim()) {
    throw new Error(`${ctx}.${key} must be a non-empty string`)
  }
  return val
}

function requireSection(record: Record<string, unknown>, key: string, ctx: string): Record<string, unknown> {
  const val = record[key]
  if (!isObjectRecord(val)) {
    throw new Error(`${ctx}.${key} must be an object`)
  }
  return val
}

function requireBboxRange(value: unknown, ctx: string): void {
  const section = isObjectRecord(value) ? value : null
  if (!section) throw new Error(`${ctx} must be an object`)
  for (const [axis, minBound, maxBound] of [['lat', -90, 90], ['lng', -180, 180]] as const) {
    const pair = section[axis]
    if (!Array.isArray(pair) || pair.length !== 2) {
      throw new Error(`${ctx}.${axis} must be [min, max]`)
    }
    const [lo, hi] = pair
    if (typeof lo !== 'number' || typeof hi !== 'number' || lo >= hi || lo < minBound || hi > maxBound) {
      throw new Error(`${ctx}.${axis} must be valid ordered bounds`)
    }
  }
}

export function validateProvinceConfig(raw: unknown): ProvinceConfig {
  if (!isObjectRecord(raw) || raw.schemaVersion !== 1) {
    throw new Error('ProvinceConfig root must be an object with schemaVersion=1')
  }
  const identity = requireSection(raw, 'identity', 'root')
  const bounds = requireSection(raw, 'bounds', 'root')
  const areas = requireSection(raw, 'areas', 'root')
  const weather = requireSection(raw, 'weather', 'root')
  const tide = requireSection(raw, 'tide', 'root')
  const guards = requireSection(raw, 'contentGuards', 'root')
  const home = requireSection(raw, 'home', 'root')
  const deploy = requireSection(raw, 'deploy', 'root')

  const siteUrl = requireText(identity, 'siteUrl', 'identity')
  if (!siteUrl.startsWith('https://')) {
    throw new Error('identity.siteUrl must start with https://')
  }
  requireText(identity, 'slug', 'identity')
  requireText(identity, 'provinceName', 'identity')
  requireText(identity, 'domain', 'identity')
  requireText(identity, 'storagePrefix', 'identity')

  requireBboxRange(bounds.schemaBbox, 'bounds.schemaBbox')
  requireBboxRange(bounds.ingestBbox, 'bounds.ingestBbox')
  requireText(bounds, 'spatialBox', 'bounds')

  requireText(areas, 'canonicalAreaSlug', 'areas')
  requireText(areas, 'canonicalRegionId', 'areas')
  requireSection(areas, 'multiRegionMeta', 'areas')
  if (!Array.isArray(areas.items) || areas.items.length === 0) {
    throw new Error('areas.items must be a non-empty array')
  }

  requireSection(weather, 'measurePoint', 'weather')
  if (typeof tide.riverAzimuthSeaward !== 'number' || typeof tide.riverAzimuthLandward !== 'number') {
    throw new Error('tide azimuth values must be numeric')
  }
  if (!Array.isArray(raw.emergencyHotlines)) {
    throw new Error('emergencyHotlines must be an array')
  }
  if (!Array.isArray(guards.outOfProvincePatterns)) {
    throw new Error('contentGuards.outOfProvincePatterns must be an array')
  }
  requireSection(home, 'curatedShowcase', 'home')
  requireSection(home, 'culinaryTrail', 'home')
  requireSection(home, 'riversideStays', 'home')
  requireText(deploy, 'appDir', 'deploy')

  return raw as unknown as ProvinceConfig
}

export function buildProvinceAreaMeta(cfg: ProvinceConfig): Record<string, AreaMetaEntry> {
  const result: Record<string, AreaMetaEntry> = {}
  for (const item of cfg.areas.items) {
    result[item.slug] = {
      name: item.name,
      emoji: item.emoji,
      icon: item.icon,
      blurb: item.blurb,
      distance: item.distance,
      hub: item.hub,
    }
  }
  const multi = cfg.areas.multiRegionMeta
  result[multi.slug] = {
    name: multi.name,
    emoji: multi.emoji,
    icon: multi.icon,
    blurb: multi.blurb,
    distance: multi.distance,
    hub: multi.hub,
  }
  return result
}

export const PROVINCE_CONFIG: ProvinceConfig = Object.freeze(validateProvinceConfig(rawProvinceConfig))

export const PROVINCE_SITE_URL = PROVINCE_CONFIG.identity.siteUrl
export const PROVINCE_DEFAULT_OG = PROVINCE_CONFIG.identity.ogImagePath.startsWith('http')
  ? PROVINCE_CONFIG.identity.ogImagePath
  : `${PROVINCE_SITE_URL}${PROVINCE_CONFIG.identity.ogImagePath}`
export const PROVINCE_STORAGE_PREFIX = PROVINCE_CONFIG.identity.storagePrefix
export const PROVINCE_CANONICAL_AREA_SLUG = PROVINCE_CONFIG.areas.canonicalAreaSlug
export const PROVINCE_CANONICAL_REGION_ID = PROVINCE_CONFIG.areas.canonicalRegionId
export const PROVINCE_CURRENT_ALIASES: ReadonlySet<string> = new Set(
  PROVINCE_CONFIG.areas.currentProvinceAliases.map(v => v.trim().toLowerCase()),
)
export const PROVINCE_AREA_META: Record<string, AreaMetaEntry> = buildProvinceAreaMeta(PROVINCE_CONFIG)
export const PROVINCE_CURRENT_AREA_META: Record<string, AreaMetaEntry> = {
  [PROVINCE_CANONICAL_AREA_SLUG]: PROVINCE_AREA_META[PROVINCE_CANONICAL_AREA_SLUG]!,
}
