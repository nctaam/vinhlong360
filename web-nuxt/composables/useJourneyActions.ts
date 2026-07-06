export type JourneyActionTone = 'primary' | 'map' | 'planner' | 'community' | 'saved' | 'neutral' | 'warning' | 'danger' | 'admin'

export interface JourneyAction {
  id: string
  icon: string
  label: string
  text?: string
  to: string
  tone?: JourneyActionTone
}

function cleanQuery(q: string | undefined) {
  return String(q || '').trim()
}

function withQuery(path: string, q: string) {
  const term = cleanQuery(q)
  return term ? `${path}?q=${encodeURIComponent(term)}` : path
}

function positiveNumber(value: unknown) {
  return Math.max(0, Number(value) || 0)
}

export function useJourneyActions() {
  function searchRecoveryActions(q: string): JourneyAction[] {
    const term = cleanQuery(q)
    return [
      {
        id: 'catalog',
        icon: '🔎',
        label: term ? 'Tìm rộng trong địa điểm' : 'Khám phá địa điểm',
        text: term ? `Mở catalog với từ khóa "${term}".` : 'Duyệt toàn bộ điểm đến theo loại và khu vực.',
        to: withQuery('/dia-diem', term),
        tone: 'primary',
      },
      {
        id: 'map',
        icon: '🗺️',
        label: 'Mở bản đồ',
        text: 'Chuyển sang khám phá theo vị trí và khu vực.',
        to: '/ban-do',
        tone: 'map',
      },
      {
        id: 'community',
        icon: '💬',
        label: 'Hỏi cộng đồng',
        text: 'Đặt câu hỏi khi hệ thống chưa có nội dung phù hợp.',
        to: term ? `/cong-dong?q=${encodeURIComponent(term)}` : '/cong-dong',
        tone: 'community',
      },
    ]
  }

  function searchSuccessActions(q: string, resultCount: number): JourneyAction[] {
    const term = cleanQuery(q)
    const actions: JourneyAction[] = []
    if (resultCount > 0) {
      actions.push({
        id: 'map',
        icon: '🗺️',
        label: 'Xem trên bản đồ',
        text: 'Đổi sang chế độ vị trí để so sánh các điểm gần nhau.',
        to: withQuery('/ban-do', term),
        tone: 'map',
      })
      actions.push({
        id: 'planner',
        icon: '📋',
        label: 'Tạo lịch trình',
        text: 'Chọn các điểm phù hợp rồi sắp xếp thành chuyến đi.',
        to: '/tao-lich-trinh',
        tone: 'planner',
      })
    }
    if (term) {
      actions.push({
        id: 'catalog',
        icon: '🔎',
        label: 'Lọc sâu hơn',
        text: 'Mở catalog để thêm bộ lọc loại hình và khu vực.',
        to: withQuery('/dia-diem', term),
        tone: 'primary',
      })
    }
    return actions.slice(0, 3)
  }

  function savedWorkspaceActions(input: {
    entityCount: number
    itineraryCount: number
    query?: string
    activeTab?: string
  }): JourneyAction[] {
    const query = cleanQuery(input.query)
    const actions: JourneyAction[] = []
    if (input.entityCount > 0) {
      actions.push({
        id: 'saved-to-plan',
        icon: '📋',
        label: 'Tạo lịch trình từ đã lưu',
        text: `${input.entityCount} địa điểm có thể đưa vào kế hoạch.`,
        to: '/tao-lich-trinh?source=saved',
        tone: 'planner',
      })
      actions.push({
        id: 'saved-map',
        icon: '🗺️',
        label: 'Xem các điểm trên bản đồ',
        text: 'Dùng bản đồ để nhóm các điểm gần nhau.',
        to: query ? `/ban-do?source=saved&q=${encodeURIComponent(query)}` : '/ban-do?source=saved',
        tone: 'map',
      })
    } else {
      actions.push({
        id: 'discover',
        icon: '🔎',
        label: 'Tìm điểm để lưu',
        text: 'Bắt đầu với danh sách điểm đến và đặc sản nổi bật.',
        to: '/dia-diem',
        tone: 'primary',
      })
    }
    if (input.itineraryCount === 0) {
      actions.push({
        id: 'planner',
        icon: '🧭',
        label: 'Mở bộ lập lịch trình',
        text: 'Tạo kế hoạch riêng trước khi đi.',
        to: '/tao-lich-trinh',
        tone: 'planner',
      })
    }
    if (query) {
      actions.unshift({
        id: 'search-system',
        icon: '🔎',
        label: 'Tìm trên toàn hệ thống',
        text: `Không chỉ trong mục đã lưu: "${query}".`,
        to: `/tim-kiem?q=${encodeURIComponent(query)}`,
        tone: 'primary',
      })
    }
    return actions.slice(0, 3)
  }

  function homepageDecisionActions(input: {
    isLoggedIn: boolean
    savedCount: number
    recentCount: number
    currentMonth: string | number
    heroFeatureName?: string
    heroFeaturePlannerPath?: string
    upcomingEventName?: string
    upcomingEventPath?: string
    communityPostCount?: number
  }): JourneyAction[] {
    const savedCount = positiveNumber(input.savedCount)
    const recentCount = positiveNumber(input.recentCount)
    const actions: JourneyAction[] = []

    // Personal-only: the editorial "what's on now" lives in the decision index (index.vue).
    // This rail is strictly the returning-user's own resume points — no event/heroFeature/
    // map/community echoes (those duplicated the index). Empty for anon/first-timers → hidden.
    if (input.isLoggedIn && savedCount > 0) {
      actions.push({
        id: 'home-continue-saved',
        icon: '💾',
        label: 'Tiếp tục từ mục đã lưu',
        text: `${savedCount} mục đã lưu có thể gom thành lịch trình.`,
        to: '/tao-lich-trinh?source=saved',
        tone: 'planner',
      })
    }

    if (recentCount > 0) {
      actions.push({
        id: 'home-recent',
        icon: '🕘',
        label: 'Nối tiếp điểm vừa xem',
        text: `${recentCount} nội dung gần đây, mở lại để so sánh trước khi lưu.`,
        to: '/da-luu?tab=recent',
        tone: 'neutral',
      })
    }

    return actions.slice(0, 2)
  }

  // (declutter-2 A7: builder userCpJourneyActions đã xoá — rail tai-khoan bị bỏ vì
  // trùng panel "Việc nên làm tiếp"; builder không còn caller nào.)

  function adminOpsActions(input: {
    healthStatus?: string
    releaseGateOk?: boolean
    deployHealthBlocking?: boolean
    deployHostConfigured?: boolean
    rollbackReady?: boolean
    queues?: Record<string, number>
    dataQualityCoverage?: number
  }): JourneyAction[] {
    const queues = input.queues || {}
    const moderation = positiveNumber(queues.moderation)
    const reports = positiveNumber(queues.reports)
    const dataQuality = positiveNumber(queues.data_quality)
    const media = positiveNumber(queues.media)
    const actions: JourneyAction[] = []

    if (input.healthStatus && input.healthStatus !== 'ok') {
      actions.push({
        id: 'admin-health',
        icon: '⚠️',
        label: 'Kiểm tra hệ thống degraded',
        text: 'Health/internal đang báo cần chú ý trước khi xử lý nội dung.',
        to: '/admin/thong-ke',
        tone: 'danger',
      })
    }
    if (!input.releaseGateOk || !input.deployHealthBlocking || !input.deployHostConfigured) {
      actions.push({
        id: 'admin-release',
        icon: '🚦',
        label: 'Khóa lại release gate',
        text: input.deployHostConfigured === false ? 'Thiếu cấu hình deploy host hoặc gate chưa đủ chặt.' : 'Đảm bảo gate chặn deploy khi smoke/health lỗi.',
        to: '/admin/ai',
        tone: 'warning',
      })
    }
    if (!input.rollbackReady) {
      actions.push({
        id: 'admin-rollback',
        icon: '🛟',
        label: 'Chuẩn bị rollback',
        text: 'Chưa thấy backup gần nhất, nên tạo backup trước batch dữ liệu lớn.',
        to: '/admin/nhat-ky',
        tone: 'warning',
      })
    }
    if (moderation > 0 || reports > 0) {
      actions.push({
        id: 'admin-moderation',
        icon: '🛡️',
        label: 'Dọn hàng đợi kiểm duyệt',
        text: `${moderation} mục kiểm duyệt và ${reports} báo cáo đang chờ xử lý.`,
        to: moderation >= reports ? '/admin/kiem-duyet' : '/admin/bao-cao',
        tone: 'admin',
      })
    }
    if (dataQuality > 0 || Number(input.dataQualityCoverage || 100) < 85) {
      actions.push({
        id: 'admin-data-quality',
        icon: '🔎',
        label: 'Xử lý quality queue',
        text: dataQuality > 0 ? `${dataQuality} candidate dữ liệu cần duyệt hoặc apply.` : `Coverage dữ liệu đang ở ${input.dataQualityCoverage || 0}%.`,
        to: '/admin/data-quality',
        tone: 'primary',
      })
    }
    if (media > 0) {
      actions.push({
        id: 'admin-media',
        icon: '🖼️',
        label: 'Duyệt media',
        text: `${media} ảnh hoặc media đang chờ kiểm tra.`,
        to: '/admin/media',
        tone: 'saved',
      })
    }
    if (!actions.length) {
      actions.push({
        id: 'admin-all-clear',
        icon: '✓',
        label: 'Tiếp tục audit định kỳ',
        text: 'Không có tín hiệu khẩn cấp; ưu tiên rà soát dữ liệu và nhật ký.',
        to: '/admin/data-quality',
        tone: 'neutral',
      })
    }

    return actions.slice(0, 4)
  }

  function dataQualityQueueActions(input: {
    autoApply: number
    needsReview: number
    reject: number
    missingSource: number
    missingLocation: number
    missingPlaceId: number
    selectedAuto: number
    bucket?: string
  }): JourneyAction[] {
    const autoApply = positiveNumber(input.autoApply)
    const needsReview = positiveNumber(input.needsReview)
    const reject = positiveNumber(input.reject)
    const selectedAuto = positiveNumber(input.selectedAuto)
    const missingSource = positiveNumber(input.missingSource)
    const missingLocation = positiveNumber(input.missingLocation)
    const missingPlaceId = positiveNumber(input.missingPlaceId)
    const actions: JourneyAction[] = []

    if (selectedAuto > 0) {
      actions.push({
        id: 'dq-dry-run-selected',
        icon: '🧪',
        label: 'Dry-run trước khi apply',
        text: `${selectedAuto} candidate đã chọn, nên xem diff trước khi ghi dữ liệu public.`,
        to: '/admin/data-quality',
        tone: 'primary',
      })
    } else if (autoApply > 0) {
      actions.push({
        id: 'dq-select-auto',
        icon: '✅',
        label: 'Chọn nhóm auto-apply',
        text: `${autoApply} candidate đủ evidence có thể xử lý theo batch.`,
        to: '/admin/data-quality?bucket=auto_apply',
        tone: 'primary',
      })
    }
    if (needsReview > 0) {
      actions.push({
        id: 'dq-review',
        icon: '👁️',
        label: 'Duyệt candidate cần người xem',
        text: `${needsReview} candidate cần kiểm tra evidence trước khi apply.`,
        to: '/admin/data-quality?bucket=needs_review',
        tone: 'warning',
      })
    }
    if (missingSource + missingLocation + missingPlaceId > 0) {
      actions.push({
        id: 'dq-gap',
        icon: '📌',
        label: 'Ưu tiên lỗ hổng dữ liệu',
        text: `${missingSource} thiếu nguồn, ${missingLocation} thiếu tọa độ, ${missingPlaceId} thiếu placeId.`,
        to: '/admin/data-quality',
        tone: 'admin',
      })
    }
    if (reject > 0) {
      actions.push({
        id: 'dq-reject',
        icon: '🧹',
        label: 'Rà soát nhóm loại',
        text: `${reject} candidate bị đánh dấu reject, nên kiểm tra mẫu lỗi lặp.`,
        to: '/admin/data-quality?bucket=reject',
        tone: 'neutral',
      })
    }

    return actions.slice(0, 4)
  }

  return {
    searchRecoveryActions,
    searchSuccessActions,
    savedWorkspaceActions,
    homepageDecisionActions,
    adminOpsActions,
    dataQualityQueueActions,
  }
}
