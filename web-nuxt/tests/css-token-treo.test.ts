// Không một `var(--x)` KHÔNG DỰ PHÒNG nào được trỏ tới token chưa từng khai.
//
// VÌ SAO CẦN: CSS custom property không khai và không có dự phòng thì khai báo
// chứa nó thành "invalid at computed-value time" — trình duyệt BỎ HẲN dòng đó,
// im lặng, không cảnh báo, không hiện trong bất kỳ test render nào. Nó chỉ lộ ra
// khi có người nhìn đúng thành phần đó trên trang.
//
// Đã xảy ra: `layouts/admin.vue` có `background: var(--surface-alt)` trong khi
// `--surface-alt` xuất hiện ĐÚNG MỘT LẦN trong toàn frontend — chính lần dùng đó.
// Ô chi tiết lỗi của AdminCP vì thế không có nền. Token đúng là `--bg-alt`, vốn
// đã được dùng 4 chỗ khác trong cùng file.
//
// PHẠM VI CÓ CHỦ Ý: chỉ soi `var(--x)` KHÔNG dự phòng. Dạng có dự phòng
// (`var(--x, #fff)`) vẫn render đúng ngay cả khi `--x` trôi tên, nên nó là nợ
// đặt-tên chứ không phải lỗi vỡ hình — đo 2026-08-30 có 13 chỗ như vậy, để lại
// cho đợt dọn token riêng.
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

import { describe, expect, it } from 'vitest'

// `process.cwd()` là web-nuxt/ khi vitest chạy — cùng cách `smoke.test.ts` dùng.
// `import.meta.url` KHÔNG dùng được ở đây: Nuxt phục vụ file test qua tiền tố ảo
// `/@fs/`, nên nó cho ra một đường dẫn lồng nhau và readdirSync ném ENOENT.
const ROOT = process.cwd()
// `tests` bị loại có chủ ý, hai lý do. (1) Không phải CSS được giao cho trình
// duyệt. (2) Bẫy tự-quy-chiếu đã cắn ngay lượt chạy đầu: chú thích của CHÍNH file
// này viết `var(--surface-alt)` làm ví dụ, và bộ quét bắt luôn nó — đúng lớp bẫy
// CLAUDE.md §5c ghi ("checker so chuỗi bắt luôn cái test đang cấm điều đó").
// Build-time scripts are not browser-delivered styles. Several scanner scripts
// intentionally contain hostile `var(--token)` fixtures, so including them
// would make this production CSS audit self-report its own test data.
const BO_QUA = new Set(['node_modules', '.nuxt', '.output', 'dist', '.git', 'tests', 'scripts'])
const DUOI = /\.(css|vue|ts|js|mjs)$/

function quetFile(thuMuc: string, ra: string[] = []): string[] {
  for (const ten of readdirSync(thuMuc)) {
    if (BO_QUA.has(ten)) continue
    const duong = join(thuMuc, ten)
    if (statSync(duong).isDirectory()) quetFile(duong, ra)
    else if (DUOI.test(ten)) ra.push(duong)
  }
  return ra
}

describe('token CSS treo', () => {
  it('mọi var(--x) không dự phòng đều trỏ tới một token có khai', () => {
    const files = quetFile(ROOT)
    const daKhai = new Set<string>()
    const dungKhongDuPhong: Array<{ ten: string, o: string }> = []

    for (const duong of files) {
      const noi = readFileSync(duong, 'utf8')
      // Khai trong stylesheet: `--x: giá trị`
      for (const m of noi.matchAll(/(--[a-zA-Z0-9-]+)\s*:/g)) daKhai.add(m[1]!)
      // Đặt lúc chạy: :style="{ '--x': ... }" hoặc setProperty('--x', ...)
      for (const m of noi.matchAll(/['"](--[a-zA-Z0-9-]+)['"]\s*[:,]/g)) daKhai.add(m[1]!)
      for (const m of noi.matchAll(/setProperty\(\s*['"`](--[a-zA-Z0-9-]+)/g)) daKhai.add(m[1]!)
      // Dùng KHÔNG dự phòng: `var(--x)` — không có dấu phẩy trước dấu đóng.
      for (const m of noi.matchAll(/var\(\s*(--[a-zA-Z0-9-]+)\s*\)/g)) {
        dungKhongDuPhong.push({ ten: m[1]!, o: relative(ROOT, duong).replace(/\\/g, '/') })
      }
    }

    // Chống rào-rỗng: nếu regex hỏng thì hai tập tụt về 0 và test "xanh" vô nghĩa.
    expect(daKhai.size, 'không quét được token nào — regex khai báo hỏng?').toBeGreaterThan(300)
    expect(dungKhongDuPhong.length, 'không quét được lần dùng nào — regex var() hỏng?')
      .toBeGreaterThan(500)

    const treo = dungKhongDuPhong.filter(x => !daKhai.has(x.ten))
    const thongDiep = treo.map(x => `  ${x.ten}  ←  ${x.o}`).join('\n')
    expect(treo, `token dùng mà chưa từng khai (trình duyệt sẽ BỎ HẲN khai báo đó):\n${thongDiep}`)
      .toHaveLength(0)
  })
})
