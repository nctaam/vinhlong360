import type { Post } from '~/types'

type CommunityPostLike = Partial<Post> & Record<string, any>

const productionTestPostPhrases = [
  'đây là test của admin',
  'day la test cua admin',
  'test admin',
]
const explicitSeedMarkers = new Set(['seed', 'demo', 'test', 'staging'])
const truthySeedMarkers = new Set(['1', 'true', 'yes', 'y', 'seed', 'demo', 'test', 'staging'])

function normalizeCommunityText(value: unknown) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
}

function stringifyCommunityValue(value: unknown) {
  if (value == null) return ''
  if (typeof value === 'string') return value
  try { return JSON.stringify(value) } catch { return String(value) }
}

function isExplicitSeedFlag(value: unknown) {
  if (value === true) return true
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') return truthySeedMarkers.has(normalizeCommunityText(value))
  return false
}

function communityPostSearchText(post: CommunityPostLike) {
  return normalizeCommunityText([
    post.content,
    post.repost?.content,
    post.repost?.author,
    stringifyCommunityValue(post.repost_snapshot),
  ].filter(Boolean).join(' '))
}

function isProductionTestPost(post: CommunityPostLike) {
  const content = communityPostSearchText(post)
  const moderation = normalizeCommunityText(post.moderation_status)
  const source = normalizeCommunityText(post.source || post.origin || post.dataset || post.environment)
  const explicitFlag = [post.is_seed, post.seed, post.demo_only, post._seed, post._demo].some(isExplicitSeedFlag)
  if (explicitFlag) return true
  if (explicitSeedMarkers.has(moderation) || explicitSeedMarkers.has(source)) return true
  return productionTestPostPhrases.some(phrase => content.includes(normalizeCommunityText(phrase)))
}

export function useCommunityPostFilters<T extends Partial<Post> = Post>() {
  function filterCommunityPosts(rawPosts: T[]) {
    const seen = new Set<string>()
    return rawPosts.filter((post) => {
      const id = String(post?.id || '')
      if (!id || seen.has(id) || isProductionTestPost(post as CommunityPostLike)) return false
      seen.add(id)
      return true
    })
  }

  function mergeCommunityPosts(current: T[], incoming: T[]) {
    const existing = new Set(current.map(post => String(post.id || '')))
    return [...current, ...incoming.filter(post => !existing.has(String(post.id || '')))]
  }

  return {
    communityPostSearchText,
    filterCommunityPosts,
    isProductionTestPost,
    mergeCommunityPosts,
  }
}
