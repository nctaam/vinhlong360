export interface Coordinates {
  lat: number
  lng: number
}

export interface EntitySource {
  url?: string
  name?: string
  date?: string
}

export interface EntitySourceFreshness {
  source_title?: string | null
  source_url?: string | null
  updated_at?: string | null
  days_since_update?: number | null
  freshness_status?: 'fresh' | 'aging' | 'stale' | 'unknown' | string
}

export interface EntitySeason {
  months?: number[]
  peak?: number[]
  text?: string
}

export interface EntityRelationship {
  source_id: string
  target_id: string
  rel_type: string
  other_id: string
  other_name: string
  other_type?: string
  other_area?: string
  distance_km?: number
}

export interface EntityAttributes extends Record<string, any> {
  address?: string
  phone?: string
  website?: string
  zalo?: string
  hours?: string
  price?: string
  fee?: string
  area_km2?: string | number
  population?: string | number
  office_kind?: string
  coords_approximate?: boolean
  amenities?: string[] | string
  price_range?: string
  atmosphere?: string
  famous_for?: string
  significance?: string
  highlight?: string
  booking_note?: string
  best_time?: string
  transport?: string
  parking?: string
  travel_tips?: string[] | string
  suggested_duration?: string
  suitable_for?: string[] | string
  family_friendly?: boolean
  must_order?: string[] | string
  signature_dish?: string
  best_dish?: string
  specialty?: string[] | string
  ingredients?: string[] | string
  ocop?: string | number
}

export interface EntityQuality extends Record<string, unknown> {
  has_source?: boolean
  source_title?: string
  source_url?: string
  source_tier?: string
  verified_at?: string
  confidence_reason?: string
}

export interface Entity {
  id: string
  type: string
  name: string
  summary?: string
  placeId?: string
  place_name?: string
  confidence?: number
  season?: EntitySeason
  attributes?: EntityAttributes
  source?: EntitySource[]
  images?: string[]
  image_urls?: string[]
  image?: string
  image_credits?: { author?: string; license?: string }[]
  coordinates?: Coordinates | [number, number] | null
  updatedAt?: string
  area?: string
  place_area?: string
  level?: string
  parentId?: string
  legacyArea?: string
  coords_approximate?: boolean
  description?: string
  relationship_total?: number
  relationships?: EntityRelationship[]
  quality?: EntityQuality
  source_freshness?: EntitySourceFreshness
  verified?: boolean
}

export interface Relationship {
  from: string
  to: string
  type: string
}

export interface ItineraryStop {
  entityId?: string
  entity_id?: string
  id?: string
  type?: string
  name?: string
  summary?: string
  duration?: string
  time?: string
  note?: string
  order?: number
  coordinates?: Coordinates | [number, number] | null
}

export interface ItineraryDay {
  day: number
  title?: string
  stops: ItineraryStop[]
}

export interface Itinerary {
  id: string
  title: string
  name?: string
  slug?: string
  summary?: string
  description?: string
  days: ItineraryDay[]
  stops?: ItineraryStop[]
  tags?: string[]
  duration?: string
  difficulty?: string
  region?: string
  area?: string
  areas?: string[]
  updatedAt?: string
  error?: string | boolean
}

export interface User {
  id: string
  phone?: string
  display_name?: string | null
  full_name?: string | null
  avatar_url?: string | null
  avatar?: string | null
  cover_url?: string | null
  username?: string | null
  bio?: string
  role?: string
  is_private?: boolean
  created_at?: string
  date_of_birth?: string | null
  email?: string | null
  contact_info?: string | null
  has_password?: boolean
  post_count?: number
  review_count?: number
  follower_count?: number
  following_count?: number
}

export interface Post {
  id: string
  user_id: string
  content: string
  images?: string[]
  created_at: string
  updated_at?: string
  like_count?: number
  likes?: number
  comment_count?: number
  comments_count?: number
  user?: User
  display_name?: string
  username?: string
  avatar?: string
  phone?: string
  liked_by_me?: boolean
  user_liked?: boolean
  bookmarked_by_me?: boolean
  user_bookmarked?: boolean
  post_type?: string
  post_type_label?: string
  rating?: number
  hashtags?: string[]
  mentions?: Mention[]
  entity_id?: string
  entity_name?: string
  entity_emoji?: string
  moderation_status?: string
  best_answer_id?: string
  repost?: { id: string; content?: string; author?: string }
}

export interface Comment {
  id: string
  post_id: string
  user_id: string
  content: string
  created_at: string
  user?: User
}

export interface Review {
  id: string
  user_id: string
  avatar_url?: string
  avatar?: string
  display_name?: string
  username?: string
  content?: string
  rating?: number
  likes?: number
  user_liked?: boolean
  created_at?: string
  images?: string[]
}

export interface Mention {
  type: 'user' | 'entity'
  id: string
  label: string
  sub?: string
}

export interface Media {
  url: string
  entity_id: string
  entity_name?: string
  entity_type?: string
  credit?: string
  license?: string
  usage_count?: number
}

export interface FetchError {
  response?: { status: number; _data?: { detail?: string; message?: string } }
  data?: { detail?: string; message?: string }
  message?: string
  statusCode?: number
}

export interface ReviewFeedResponse {
  posts: Review[]
  rating?: { avg: number; count: number }
  total: number
}

export interface Notification {
  id: string
  type: string
  title?: string
  body?: string
  link?: string
  read: boolean
  is_read?: boolean
  ref_type?: string
  ref_id?: string
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  suggestions?: string[]
  tool_calls?: ChatToolCall[]
}

export interface ChatToolCall {
  name: string
  result?: unknown
}

export interface ChatResponse {
  reply: string
  suggestions: string[]
  tool_calls: ChatToolCall[]
}

export interface Place {
  id: string
  name: string
  level?: string
  area?: string
  parent_id?: string
  coordinates?: Coordinates | [number, number] | null
}

export interface Report {
  id: string
  target_type: string
  target_id: string
  reason: string
  status?: string
  created_at: string
  reporter_id?: string
}

export interface InfoReport {
  id: string
  entity_id?: string
  place_id?: string
  field: string
  old_value?: string
  new_value: string
  status: string
  created_at: string
  user_id?: string
}

export interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration: number
}

export interface ConfirmState {
  open: boolean
  title: string
  message: string
  confirmText: string
  cancelText: string
  danger: boolean
}

