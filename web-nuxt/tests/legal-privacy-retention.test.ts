import { describe, expect, it } from 'vitest'

import privacyPolicy from '#privacy-policy'
import { LEGAL_PRIVACY } from '../utils/legalContent'

describe('privacy retention authority', () => {
  it('renders the committed account-erasure deadline', () => {
    expect(privacyPolicy.accountErasureDeadlineDays).toBe(30)
    const rights = LEGAL_PRIVACY.sections.find(section => section.heading.startsWith('4.'))
    expect(rights?.body).toContain('30 ngày kể từ khi yêu cầu xoá tài khoản')
    expect(rights?.body).not.toContain('20 ngày')
  })
})
