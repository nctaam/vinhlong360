import { describe, expect, it } from 'vitest'

import { resolveDetailAction, resolveDetailFetchError } from '../utils/detailExperience'

const selectedContext = {
  family: 'entity',
  id: 'cho-ben-tre',
} as const

describe('detail fetch error resolution', () => {
  it('maps only an API-confirmed not_found response to not-found', () => {
    expect(resolveDetailFetchError({
      statusCode: 404,
      data: { detail: 'not_found' },
    })).toEqual({ kind: 'not_found' })

    expect(resolveDetailFetchError({ statusCode: 404, message: 'route unavailable' }))
      .toEqual({ kind: 'error', retryable: true })
  })

  it.each([
    { statusCode: 404, kind: 'not_found' },
    { statusCode: 404, detail: 'not_found' },
    { statusCode: 404, message: 'not_found' },
    { statusCode: 404, statusMessage: 'not_found' },
  ])('does not trust forged top-level absence metadata %#', (failure) => {
    expect(resolveDetailFetchError(failure)).toEqual({ kind: 'error', retryable: true })
  })

  it('requires an exact trusted API detail value', () => {
    expect(resolveDetailFetchError({
      response: { status: 404, _data: { detail: 'not_found' } },
    })).toEqual({ kind: 'not_found' })
    expect(resolveDetailFetchError({
      statusCode: 404,
      data: { detail: 'not_found' },
    })).toEqual({ kind: 'not_found' })
    expect(resolveDetailFetchError({
      statusCode: 404,
      data: { detail: ' NOT_FOUND ' },
    })).toEqual({ kind: 'error', retryable: true })
    expect(resolveDetailFetchError({
      response: { status: 404, _data: { detail: 'route unavailable' } },
    })).toEqual({ kind: 'error', retryable: true })
  })

  it('does not convert a timeout into not-found', () => {
    const result = resolveDetailFetchError({ statusCode: 504, kind: 'timeout' })
    expect(result).toEqual({ kind: 'error', retryable: true })
  })

  it.each([
    { statusCode: 503, kind: 'server' },
    { statusCode: 200, kind: 'parse', name: 'SyntaxError' },
    { statusCode: 0, kind: 'offline', code: 'ERR_NETWORK' },
  ])('keeps $kind failures recoverable on the current route', (failure) => {
    expect(resolveDetailFetchError(failure)).toEqual({ kind: 'error', retryable: true })
  })

  it.each(['hidden', 'private'])('keeps %s content distinct from public not-found', (detail) => {
    expect(resolveDetailFetchError({ statusCode: 403, data: { detail } }))
      .toEqual({ kind: 'hidden', retryable: false })
  })
})

describe('detail primary action resolution', () => {
  it('uses directions only when coordinates are valid', () => {
    expect(resolveDetailAction({ coords: [10.2, 105.9], phone: null }, selectedContext).id).toBe('directions')
    expect(resolveDetailAction({ coords: null, phone: '0900' }, selectedContext).id).toBe('call')
  })

  it.each([
    [null, '0900'],
    [[null, null], '0900'],
    [['', ''], '0900'],
    [[false, false], '0900'],
    [[10.2, 105.9, 106], '0900'],
    [[91, 105.9], '0900'],
    [[10.2, 181], '0900'],
    [[Number.NaN, 105.9], '0900'],
  ] as const)('falls back to a real phone when coordinates %j are unusable', (coords, phone) => {
    const action = resolveDetailAction({ coords, phone }, selectedContext)
    expect(action).toMatchObject({ id: 'call', href: 'tel:0900' })
  })

  it('uses one deterministic context action when directions and phone are absent', () => {
    expect(resolveDetailAction({ coords: null, phone: null }, selectedContext)).toEqual({
      id: 'plan',
      label: 'Thêm vào lịch trình',
      href: '/tao-lich-trinh?add=cho-ben-tre',
    })
    expect(resolveDetailAction({ coords: null, phone: null }, { family: 'ward', id: 'p-an-hoi' })).toEqual({
      id: 'browse',
      label: 'Xem địa điểm trong khu vực',
      href: '/danh-ba',
    })
  })

  it('never fabricates a call action from an invalid phone', () => {
    expect(resolveDetailAction({ coords: null, phone: 'đang cập nhật' }, selectedContext).id).toBe('plan')
  })

  it('keeps explicitly numeric zero coordinates valid', () => {
    expect(resolveDetailAction({ coords: [0, 105.9], phone: null }, selectedContext)).toMatchObject({
      id: 'directions',
      href: '/ban-do?id=cho-ben-tre&lat=0&lng=105.9',
    })
    expect(resolveDetailAction({ coords: [10.2, 0], phone: null }, selectedContext)).toMatchObject({
      id: 'directions',
      href: '/ban-do?id=cho-ben-tre&lat=10.2&lng=0',
    })
  })
})
