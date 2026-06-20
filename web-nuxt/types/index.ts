export interface Coordinates {
  lat: number
  lng: number
}

export interface EntitySource {
  url?: string
  name?: string
  date?: string
}

export interface EntitySeason {
  months?: number[]
  peak?: number[]
  text?: string
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
  attributes?: Record<string, string | number | boolean | string[]>
  source?: EntitySource[]
  images?: string[]
  coordinates?: Coordinates | [number, number] | null
  updatedAt?: string
  area?: string
  place_area?: string
  level?: string
  parentId?: string
  legacyArea?: string
}

export interface Relationship {
  from: string
  to: string
  type: string
}

export interface ItineraryStop {
  entity_id: string
  name?: string
  duration?: string
  note?: string
  order?: number
}

export interface ItineraryDay {
  day: number
  title?: string
  stops: ItineraryStop[]
}

export interface Itinerary {
  id: string
  title: string
  slug?: string
  summary?: string
  days: ItineraryDay[]
  tags?: string[]
  duration?: string
  difficulty?: string
  region?: string
  area?: string
  updatedAt?: string
}

export interface User {
  id: string
  display_name?: string
  avatar_url?: string
  role?: string
  created_at?: string
}

export interface Post {
  id: string
  user_id: string
  content: string
  images?: string[]
  created_at: string
  updated_at?: string
  like_count?: number
  comment_count?: number
  user?: User
  liked_by_me?: boolean
  bookmarked_by_me?: boolean
}

export interface Comment {
  id: string
  post_id: string
  user_id: string
  content: string
  created_at: string
  user?: User
}

export interface Notification {
  id: string
  type: string
  title?: string
  body?: string
  link?: string
  read: boolean
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

export interface SmartSearchResult {
  reply: string
  entities: Entity[]
  suggestions: string[]
}

export interface Place {
  id: string
  name: string
  level?: string
  area?: string
  parent_id?: string
  coordinates?: Coordinates | [number, number] | null
}

export interface Facility {
  id: string
  name: string
  type?: string
  place_id?: string
  attributes?: Record<string, string | number | boolean>
}

export interface EventEntity extends Entity {
  attributes?: Record<string, string | number | boolean | string[]> & {
    category?: string
    date_start?: string
    date_end?: string
  }
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

export interface WeatherData {
  temp?: number
  description?: string
  icon?: string
  humidity?: number
}

export interface RouteLeg {
  distance: number
  duration: number
  steps: RouteStep[]
}

export interface RouteStep {
  instruction: string
  distance: number
  duration: number
}
