// The one place operator-facing case vocabulary lives.
//
// CaseQueue and CaseWorkbench each grew their own copies and the health label
// had already drifted between them ("Đang khắc phục" vs "… sự cố"). Two
// spellings of one state teach operators the UI is careless with states —
// which is the last thing a corrections desk can afford.

export const CASE_KIND_LABEL: Record<string, string> = {
  decide: 'Cần quyết định',
  decision: 'Cần quyết định',
  publication: 'Cần đăng',
  truth_review: 'Cần kiểm chứng sự thật',
  publication_review: 'Cần soát trước đăng',
  escalation: 'Cần giám sát',
  verify: 'Cần kiểm chứng',
}

export const CASE_HEALTH_LABEL: Record<string, string> = {
  on_track: 'Đúng hạn',
  at_risk: 'Sắp trễ hạn',
  breached: 'Đã trễ hạn',
  recovery: 'Đang khắc phục sự cố',
}

export const CASE_ADMIN_PUBLICATION_LABEL: Record<string, string> = {
  not_required: 'Không cần đăng',
  pending: 'Chờ đăng',
  applied: 'Đã ghi, chờ kiểm chứng',
  verified: 'Đã kiểm chứng trên trang',
  rolled_back: 'Đã hoàn tác',
}
