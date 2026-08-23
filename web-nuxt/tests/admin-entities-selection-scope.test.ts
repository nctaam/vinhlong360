import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * Tập đã chọn phải thuộc về KHUNG NHÌN hiện tại.
 *
 * bulkDelete gửi trọn `[...selected.value]` lên /admin-api/entities/bulk-delete,
 * còn hộp xác nhận chỉ nói "Xóa N entity đã chọn?" — không liệt kê là những cái
 * nào. Nếu tập đó sống sót qua việc đổi trang / đổi từ khoá / đổi bộ lọc thì chủ
 * dự án bấm Xóa sẽ xoá vĩnh viễn cả những entity đã trôi khỏi màn hình và không
 * có cách nào biết trước.
 *
 * Trang này không có test nào trước đợt 2026-08-23. Test đọc mã nguồn thay vì
 * mount vì trang tự gọi API lúc mount và kéo theo cả tầng auth; điều cần khoá ở
 * đây là một BẤT BIẾN CẤU TRÚC, và nó suy được từ chính mã: mọi ref cấp tham số
 * cho truy vấn danh sách đều phải nằm trong một watcher xoá lựa chọn.
 */
const SOURCE = readFileSync(resolve(__dirname, '../pages/admin/entities.vue'), 'utf8')

/** Các ref quyết định TẬP KẾT QUẢ đang hiển thị, đọc ra từ thân fetchEntities. */
const RESULT_SET_CANDIDATES = ['limit', 'page', 'search', 'typeFilter', 'orphansOnly']

function fetchBody(): string {
  const start = SOURCE.indexOf('async function fetchEntities')
  expect(start, 'không tìm thấy fetchEntities — test này bám vào nó').toBeGreaterThan(-1)
  // Cửa sổ rộng rãi: chỉ cần trùm thân hàm, không cần cắt chính xác dấu ngoặc.
  return SOURCE.slice(start, start + 1400)
}

function resultSetRefs(): string[] {
  const body = fetchBody()
  return RESULT_SET_CANDIDATES.filter(name => body.includes(name + '.value'))
}

/** Đoạn mã của mọi watcher có xoá lựa chọn, gộp lại. */
function selectionClearingWatchers(): string {
  const out: string[] = []
  let from = 0
  for (;;) {
    const i = SOURCE.indexOf('watch(', from)
    if (i === -1) break
    const chunk = SOURCE.slice(i, i + 420)
    if (chunk.includes('selected.value = new Set()')) out.push(chunk)
    from = i + 6
  }
  return out.join(' ')
}

describe('admin/entities — phạm vi của tập đã chọn', () => {
  it('mọi ref quyết định tập kết quả đều nằm trong watcher xoá lựa chọn', () => {
    const refs = resultSetRefs()
    // Nếu assertion này đỏ vì fetchEntities không còn dùng ref nào, hãy sửa
    // resultSetRefs() chứ đừng hạ kỳ vọng — nó là nguồn của cả test.
    expect(refs.length).toBeGreaterThanOrEqual(5)

    const watched = selectionClearingWatchers()
    expect(watched.length, 'phải có ít nhất một watcher xoá lựa chọn').toBeGreaterThan(0)

    const thieu = refs.filter(r => !watched.includes(r))
    expect(thieu, 'ref cấp tham số truy vấn nhưng KHÔNG xoá lựa chọn khi đổi: ' + thieu.join(', ')).toEqual([])
  })

  it('bulkDelete vẫn là thao tác phải xác nhận và có gắn cờ nguy hiểm', () => {
    const fn = SOURCE.slice(SOURCE.indexOf('async function bulkDelete'))
    const body = fn.slice(0, fn.indexOf('\n}\n'))
    expect(body).toContain('confirmDialog')
    expect(body).toContain('danger: true')
  })
})
