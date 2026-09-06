import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(__dirname, '..')

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(BASE_DIR, relPath), 'utf-8')
}

describe('Form Accessibility & Live Region Quality Gate (Mốc 104)', () => {
  describe('AuthModal.vue Form Controls', () => {
    const content = readFile('components/AuthModal.vue')

    it('bảo đảm tất cả các trường đăng ký có id và label for liên kết chuẩn xác', () => {
      expect(content).toContain('for="reg-fullname"')
      expect(content).toContain('id="reg-fullname"')
      expect(content).toContain('for="reg-dob"')
      expect(content).toContain('id="reg-dob"')
      expect(content).toContain('for="reg-username"')
      expect(content).toContain('id="reg-username"')
      expect(content).toContain('for="reg-password"')
      expect(content).toContain('id="reg-password"')
      expect(content).toContain('for="reg-password-confirm"')
      expect(content).toContain('id="reg-password-confirm"')
    })

    it('bảo đảm các trường đăng ký có aria-label bổ trợ cho trình đọc màn hình', () => {
      expect(content).toContain('aria-label="Họ và tên"')
      expect(content).toContain('aria-label="Ngày sinh"')
      expect(content).toContain('aria-label="Tên người dùng (username)"')
      expect(content).toContain('aria-label="Mật khẩu"')
      expect(content).toContain('aria-label="Xác nhận mật khẩu"')
    })
  })

  describe('ConfirmDialog.vue Design Token Compliance', () => {
    const content = readFile('components/ConfirmDialog.vue')

    it('bảo đảm hộp thoại xác nhận dùng token khoảng cách chuẩn thay cho px/rem thô', () => {
      expect(content).toContain('padding: var(--space-6);')
      expect(content).not.toContain('padding: 1.5rem;')
    })
  })

  describe('ChatWidget.vue Suggestions Accessibility', () => {
    const content = readFile('components/ChatWidget.vue')

    it('bảo đảm các nút gợi ý câu hỏi có aria-label định danh mục đích', () => {
      expect(content).toContain(':aria-label="\'Gợi ý hỏi: \' + s"')
    })
  })

  describe('EntityReviews.vue File Upload Accessibility', () => {
    const content = readFile('components/EntityReviews.vue')

    it('bảo đảm file input đính kèm ảnh có aria-label định danh', () => {
      expect(content).toContain('aria-label="Đính kèm hình ảnh đánh giá"')
    })
  })

  describe('da-luu.vue Live Telemetry & Form Labels', () => {
    const content = readFile('pages/da-luu.vue')

    it('bảo đảm ô tìm kiếm mục đã lưu có aria-label', () => {
      expect(content).toContain('aria-label="Tìm trong mục đã lưu"')
    })

    it('bảo đảm có vùng aria-live="polite" role="status" thông báo số lượng mục', () => {
      expect(content).toContain('role="status"')
      expect(content).toContain('aria-live="polite"')
      expect(content).toContain('Hiển thị {{ visibleCount }} mục')
    })
  })

  describe('danh-ba.vue Live Telemetry & Ward Updates', () => {
    const content = readFile('pages/danh-ba.vue')

    it('bảo đảm có vùng aria-live="polite" role="status" thông báo kết quả tìm kiếm cơ sở', () => {
      expect(content).toContain('role="status"')
      expect(content).toContain('aria-live="polite"')
      expect(content).toContain('{{ statusAnnouncement }}')
    })

    it('bảo đảm có computed statusAnnouncement xử lý đủ 5 trạng thái thông báo', () => {
      expect(content).toContain('const statusAnnouncement = computed')
      expect(content).toContain('Vui lòng chọn xã hoặc phường')
      expect(content).toContain('Đang tải danh bạ cơ quan')
      expect(content).toContain('Chưa có danh bạ cơ quan cho')
      expect(content).toContain('Đã tìm thấy')
    })
  })

  describe('lich-van-nien.vue Date Converter Inputs', () => {
    const content = readFile('pages/lich-van-nien.vue')

    it('bảo đảm cả 6 ô nhập số lịch dương và lịch âm đều có aria-label định danh', () => {
      expect(content).toContain('aria-label="Ngày dương lịch"')
      expect(content).toContain('aria-label="Tháng dương lịch"')
      expect(content).toContain('aria-label="Năm dương lịch"')
      expect(content).toContain('aria-label="Ngày âm lịch"')
      expect(content).toContain('aria-label="Tháng âm lịch"')
      expect(content).toContain('aria-label="Năm âm lịch"')
    })
  })

  describe('cai-dat.vue & nguoi-dung/[id].vue Accessible Form Fields', () => {
    const caiDatContent = readFile('pages/cai-dat.vue')
    const nguoiDungContent = readFile('pages/nguoi-dung/[id].vue')

    it('bảo đảm các ô readonly và file inputs trong cài đặt có nhãn rõ ràng', () => {
      expect(caiDatContent).toContain('aria-label="Tải lên ảnh đại diện"')
      expect(caiDatContent).toContain('aria-label="Tải lên ảnh bìa"')
      expect(caiDatContent).toContain('aria-label="Số điện thoại"')
      expect(caiDatContent).toContain('aria-label="Tên người dùng (username)"')
    })

    it('bảo đảm các ô mật khẩu và 2FA trong cài đặt có aria-label', () => {
      expect(caiDatContent).toContain('aria-label="Mật khẩu hiện tại"')
      expect(caiDatContent).toContain('aria-label="Mật khẩu mới"')
      expect(caiDatContent).toContain('aria-label="Xác nhận mật khẩu"')
      expect(caiDatContent).toContain('aria-label="Mã xác nhận 6 chữ số"')
    })

    it('bảo đảm modal tạo bộ sưu tập trong nguoi-dung/[id].vue có aria-label', () => {
      expect(nguoiDungContent).toContain('aria-label="Tên danh sách bộ sưu tập"')
      expect(nguoiDungContent).toContain('aria-label="Mô tả bộ sưu tập"')
    })
  })

  describe('Mốc 105: Input Autocomplete Semantics (WCAG 2.2 SC 1.3.5) & Focus-Visible Standards (SC 2.4.7)', () => {
    const caiDatContent = readFile('pages/cai-dat.vue')
    const intakeContent = readFile('components/cases/CorrectionIntakeForm.vue')
    const duyetAnhContent = readFile('pages/admin/duyet-anh.vue')
    const caiDatIndexContent = readFile('pages/admin/cai-dat/index.vue')

    it('bảo đảm các trường trong cài đặt có autocomplete ngữ nghĩa chuẩn', () => {
      expect(caiDatContent).toContain('autocomplete="tel"')
      expect(caiDatContent).toContain('autocomplete="username"')
      expect(caiDatContent).toContain('autocomplete="name"')
      expect(caiDatContent).toContain('autocomplete="nickname"')
      expect(caiDatContent).toContain('autocomplete="one-time-code"')
    })

    it('bảo đảm trường số điện thoại trong CorrectionIntakeForm có autocomplete="tel"', () => {
      expect(intakeContent).toContain('id="optional-phone"')
      expect(intakeContent).toMatch(/id="optional-phone"[^>]*autocomplete="tel"/)
    })

    it('bảo đảm các ô nhập liệu quản trị có focus-visible outline với token var(--color-focus)', () => {
      expect(duyetAnhContent).toContain('.img-reason-input:focus-visible')
      expect(duyetAnhContent).toContain('outline: 2px solid var(--color-focus);')
      expect(caiDatIndexContent).toContain('.cs-search-input:focus-visible')
      expect(caiDatIndexContent).toContain('outline: 2px solid var(--color-focus);')
    })
  })
})

