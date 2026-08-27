import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
// Rút hạng sao OCOP — khoá bằng CHUỖI THẬT lấy từ dữ liệu đang chạy, không phải
// chuỗi tự nghĩ ra. Mỗi ca dưới đây từng làm sai một bản luật trong lúc dựng.
import { describe, expect, it } from 'vitest'

import {
  isOcopCertified,
  ocopBadgeLabel,
  ocopClaimedStars,
  ocopStarProvisional,
  ocopStars,
} from '../utils/ocop'

const e = (attributes: Record<string, any>, summary = '') => ({ attributes, summary })

describe('ocopClaimedStars — bốn kiểu khoá', () => {
  it('đọc được khoá số ở cả ba tên', () => {
    expect(ocopClaimedStars(e({ ocop_star: 5 }))).toBe(5)
    expect(ocopClaimedStars(e({ ocop_stars: 4 }))).toBe(4)
    expect(ocopClaimedStars(e({ ocop_rating: 3 }))).toBe(3)
    expect(ocopClaimedStars(e({ ocop_star: '4' }))).toBe(4)
  })

  it('rút được hạng từ văn xuôi NEO ĐẦU CHUỖI', () => {
    // 10 chuỗi thật đo được trong attributes.ocop của dữ liệu đang chạy.
    expect(ocopClaimedStars(e({ ocop: '3 sao (2024)' }))).toBe(3)
    expect(ocopClaimedStars(e({ ocop: '4 sao' }))).toBe(4)
    expect(ocopClaimedStars(e({ ocop: '3 sao' }))).toBe(3)
    expect(ocopClaimedStars(e({ ocop: 'OCOP 3 sao' }))).toBe(3)
    expect(ocopClaimedStars(e({ ocop: 'OCOP 4 sao (2019)' }))).toBe(4)
    expect(ocopClaimedStars(e({ ocop: 'OCOP 3 sao (2020)' }))).toBe(3)
    expect(ocopClaimedStars(e({ ocop: 'OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)' }))).toBe(4)
  })

  it('KHÔNG tự phong hạng từ danh mục sản phẩm của công ty khác', () => {
    // dua-sap-cau-ke — trái dừa, không phải sản phẩm chế biến của VICOSAP. Luật
    // "tìm N sao ở bất kỳ đâu" sẽ gán 5 sao quốc gia cho nó.
    expect(ocopClaimedStars(e({
      ocop: 'VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao',
    }))).toBe(0)
  })

  it('"OCOP" trần là có chứng nhận nhưng KHÔNG rõ hạng', () => {
    expect(ocopClaimedStars(e({ ocop: 'OCOP' }))).toBe(0)
    expect(isOcopCertified(e({ ocop: 'OCOP' }))).toBe(true)
  })

  it('bỏ sót ca lành không-neo-đầu, và bỏ sót về phía AN TOÀN', () => {
    // "Cam sành Khánh Nhân, Thuận Loan — OCOP 3 sao": hạng có thật nhưng nằm
    // giữa câu. Hiện là "có chứng nhận, chưa rõ hạng" — thiệt thòi mà THẬT.
    const cam = e({ ocop: 'Cam sành Khánh Nhân, Thuận Loan — OCOP 3 sao' })
    expect(ocopClaimedStars(cam)).toBe(0)
    expect(isOcopCertified(cam)).toBe(true)
  })
})

describe('ocopStarProvisional — §1.7, hạng đề nghị không phải hạng đã đạt', () => {
  it('hạ hạng mới được ĐỀ XUẤT', () => {
    // khoai-lang-say-binh-tan, nguyên văn.
    const binhTan = e({ ocop_star: 5 },
      'Sản phẩm OCOP đặc trưng của Bình Tân, gồm khoai lang tím sấy và khoai lang '
      + 'vàng sấy, được đề xuất lên Trung ương đánh giá 5 sao OCOP, sản xuất bởi '
      + 'Công ty TNHH MTV Chế biến thực phẩm Miền Tây.')
    expect(ocopClaimedStars(binhTan)).toBe(5)
    expect(ocopStarProvisional(binhTan)).toBe(true)
    expect(ocopStars(binhTan)).toBe(0)
    // Vẫn là sản phẩm OCOP — chỉ là không lên được bậc 5 sao.
    expect(isOcopCertified(binhTan)).toBe(true)
  })

  it('KHÔNG hạ oan hạng đã ĐẠT dù cùng câu có lời đề xuất hạng cao hơn', () => {
    // khoai-lang-say-dong-phat, nguyên văn — ca giết-oan của luật một chiều.
    const dongPhat = e({ ocop_star: 4 },
      'Sản phẩm khoai lang tím sấy và khoai lang vàng sấy của Công ty TNHH Đông '
      + 'Phát Food, đạt OCOP 4 sao và được đề xuất công nhận 5 sao. Xuất khẩu sang '
      + 'Hàn Quốc.')
    expect(ocopStarProvisional(dongPhat)).toBe(false)
    expect(ocopStars(dongPhat)).toBe(4)
  })

  it('văn xuôi TỰ MÂU THUẪN: lời đề nghị thắng câu khẳng định trần', () => {
    // khoai-lang-say-binh-tan, ĐẦY ĐỦ cả summary lẫn description — nguyên văn.
    // Test cũ chỉ truyền summary nên KHÔNG bắt được: description kết bằng câu
    // trần "Sản phẩm OCOP 5 sao." làm luật xét-từng-lần lật ngược phán quyết,
    // và trang đang chạy vẫn khai 5 sao. Đây là lý do phải test bằng đúng khối
    // văn xuôi mà mã THẬT SỰ đọc, không phải một mẩu của nó.
    const binhTanDayDu = {
      attributes: { ocop_star: 5 },
      summary: 'Sản phẩm OCOP đặc trưng của Bình Tân, gồm khoai lang tím sấy và '
        + 'khoai lang vàng sấy, được đề xuất lên Trung ương đánh giá 5 sao OCOP, '
        + 'sản xuất bởi Công ty TNHH MTV Chế biến thực phẩm Miền Tây.',
      description: 'Khoai lang tím sấy và khoai lang vàng sấy của Bình Tân, được '
        + 'đề xuất lên Trung ương đánh giá 5 sao OCOP. Sản xuất bởi Công ty TNHH '
        + 'MTV Chế biến thực phẩm Miền Tây. Sản phẩm OCOP 5 sao.',
    }
    expect(ocopStarProvisional(binhTanDayDu)).toBe(true)
    expect(ocopStars(binhTanDayDu)).toBe(0)
  })

  it('văn xuôi không nhắc hạng thì tin khoá dữ liệu', () => {
    const sauRi = e({ ocop_star: 5 },
      'Sản phẩm sầu riêng sấy thăng hoa OCOP 5 sao của Công ty TNHH Sáu Ri, Long Hồ.')
    expect(ocopStars(sauRi)).toBe(5)
    expect(ocopStars(e({ ocop_star: 5 }, 'Không nhắc gì tới hạng.'))).toBe(5)
    expect(ocopStars(e({ ocop_star: 5 }))).toBe(5)
  })

  it('không có hạng thì không có gì để hạ', () => {
    expect(ocopStarProvisional(e({ ocop: 'OCOP' }, 'được đề xuất công nhận'))).toBe(false)
    expect(ocopStarProvisional(null)).toBe(false)
  })
})

describe('isOcopCertified — cái lỗ làm 73 sản phẩm biến mất', () => {
  it('nhận sản phẩm CHỈ có khoá sao số', () => {
    // Bộ lọc cũ là `attributes.ocop` truthy, nên 73 sản phẩm có ocop_star mà
    // không có ocop bị loại HẲN khỏi trang /ocop.
    expect(isOcopCertified(e({ ocop_star: 4 }))).toBe(true)
    expect(isOcopCertified(e({ ocop_certified: true }))).toBe(true)
  })

  it('không nhận entity không có dấu hiệu OCOP nào', () => {
    expect(isOcopCertified(e({ rating: 4.5 }))).toBe(false)
    expect(isOcopCertified(e({ ocop: '' }))).toBe(false)
    expect(isOcopCertified(null)).toBe(false)
    expect(isOcopCertified(undefined)).toBe(false)
  })
})

describe('ocopBadgeLabel — không bao giờ in văn xuôi thô ra giao diện', () => {
  it('rút gọn về đúng hạng', () => {
    expect(ocopBadgeLabel(e({ ocop_star: 5 }))).toBe('OCOP 5 sao')
    expect(ocopBadgeLabel(e({ ocop: 'OCOP 3 sao' }))).toBe('OCOP 3 sao')
  })

  it('có chứng nhận nhưng chưa rõ hạng thì chỉ ghi OCOP', () => {
    expect(ocopBadgeLabel(e({ ocop: 'OCOP' }))).toBe('OCOP')
    expect(ocopBadgeLabel(e({ ocop_certified: true }))).toBe('OCOP')
  })

  it('KHÔNG gán danh mục của công ty khác cho entity này', () => {
    // dua-sap-cau-ke — trang thật từng in nguyên chuỗi 56 ký tự này lên huy
    // hiệu (rộng 468px) VÀ vào JSON-LD brand.name.
    const duaSap = e({ ocop: 'VICOSAP: 4 SP OCOP 5 sao quốc gia + 7 SP OCOP 4 sao' })
    expect(ocopBadgeLabel(duaSap)).toBe('OCOP')
    expect(ocopBadgeLabel(duaSap)).not.toContain('VICOSAP')
  })

  it('KHÔNG in số quyết định lên huy hiệu', () => {
    const qd = e({ ocop: 'OCOP 4 sao (QĐ 114/QĐ-UBND, 15/1/2020)' })
    expect(ocopBadgeLabel(qd)).toBe('OCOP 4 sao')
    expect(ocopBadgeLabel(qd)).not.toContain('QĐ')
  })

  it('hạng mới ĐỀ XUẤT thì tụt về OCOP trần, không khai hạng (§1.7)', () => {
    const binhTan = {
      attributes: { ocop_star: 5 },
      summary: 'được đề xuất lên Trung ương đánh giá 5 sao OCOP.',
    }
    expect(ocopBadgeLabel(binhTan)).toBe('OCOP')
  })

  it('không có dấu hiệu OCOP thì không có nhãn', () => {
    expect(ocopBadgeLabel(e({ rating: 4 }))).toBe('')
    expect(ocopBadgeLabel(null)).toBe('')
  })
})

// ─────────────────────────────────────────────────────────────────────────
// BỘ CA DÙNG CHUNG với bản Python
// ─────────────────────────────────────────────────────────────────────────
// `tests/fixtures/ocop-twin-cases.json` (ở gốc repo) được CẢ HAI suite đọc —
// bộ này và `agent/tests/test_ocop.py`. Viết test song song ở hai bên là CHƯA
// ĐỦ: 2026-08-27 hai bản đã lệch ở việc kẹp thang 1..5 (Python trả 'OCOP' cho
// hạng 9, TS trả 'OCOP 9 sao') mà cả hai bộ test vẫn xanh, vì mỗi bên chỉ soi
// ca của riêng mình. File dùng chung biến lời hứa "hai bản khớp nhau" thành
// một phép đo.
describe('bộ ca dùng chung với bản Python', () => {
  const twin = JSON.parse(
    readFileSync(resolve(process.cwd(), '../tests/fixtures/ocop-twin-cases.json'), 'utf8'),
  ) as { cases: Array<{ ten: string; entity: any; label: string; tier: number; certified: boolean }> }

  it('bộ ca không bị teo', () => {
    expect(twin.cases.length).toBeGreaterThanOrEqual(20)
  })

  it('khớp từng ca', () => {
    const sai: string[] = []
    for (const c of twin.cases) {
      const got = [ocopBadgeLabel(c.entity), ocopStars(c.entity), isOcopCertified(c.entity)]
      const want = [c.label, c.tier, c.certified]
      if (JSON.stringify(got) !== JSON.stringify(want)) {
        sai.push(`${c.ten}: được ${JSON.stringify(got)}, cần ${JSON.stringify(want)}`)
      }
    }
    expect(sai, 'lệch bộ ca dùng chung:\n  ' + sai.join('\n  ')).toEqual([])
  })
})
