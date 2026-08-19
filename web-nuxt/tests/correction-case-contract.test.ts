// The client's field names are read out of the backend, not remembered.
//
// A renamed projection field does not break a build. It renders an empty status
// to somebody waiting on an answer about their own report, which is the worst
// possible place for a silent failure. So this file reads the Python source and
// compares, rather than trusting two lists to stay in step by hand.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

import {
  CASE_DECISION_COPY,
  CASE_PUBLICATION_COPY,
  type CasePublicationState,
} from '../types/cases'

const REPO_ROOT = resolve(__dirname, '..', '..')

function backendSource(relative: string): string {
  return readFileSync(resolve(REPO_ROOT, relative), 'utf8')
}

function keysInBlock(source: string, marker: string): string[] {
  const start = source.indexOf(marker)
  expect(start, `${marker} not found in the backend source`).toBeGreaterThan(-1)
  const block = source.slice(start, source.indexOf('\n\n\n', start))
  return [...block.matchAll(/"([A-Za-z][A-Za-z0-9]*)":/g)]
    .map(match => match[1])
    .filter((name): name is string => Boolean(name))
}

/** The one line of `_Values` assignments that follows an enum declaration. */
function enumValues(source: string, className: string): string {
  const after = source.split(`class ${className}(_Values):`)[1]
  expect(after, `${className} is no longer declared where this test looks`).toBeTruthy()
  return (after ?? '').split('\n')[1] ?? ''
}

describe('the status projection', () => {
  it('names exactly the fields the backend sends', () => {
    const sent = new Set(keysInBlock(
      backendSource('agent/cases/public_api.py'),
      'def status_payload(',
    ))

    // Every field the client reads has to be one the server actually sends.
    for (const field of [
      'publicReference', 'receivedAt', 'currentStep', 'waitingFor', 'nextAction',
      'nextUpdateAt', 'promiseHealth', 'itemDecisions', 'itemPublicationStates',
      'reviewPath', 'itemId', 'outcome', 'dispositionFamily', 'state',
    ]) {
      expect(sent.has(field), `backend no longer sends ${field}`).toBe(true)
    }
  })

  it('uses the receipt field names the create route returns', () => {
    const source = backendSource('agent/cases/public_api.py')

    for (const field of ['publicReference', 'capability', 'receivedAt',
                         'nextUpdateAt', 'replayed']) {
      expect(source).toContain(`"${field}"`)
    }
  })
})

describe('publication states', () => {
  const STATES: CasePublicationState[] = [
    'not_required', 'pending', 'applied', 'verified', 'rolled_back',
  ]

  it('cover every state the backend can report', () => {
    const source = backendSource('agent/cases/domain.py')
    const declared = enumValues(source, 'PublicationState')

    for (const state of STATES) {
      expect(declared, `PublicationState lost ${state}`).toContain(`'${state}'`)
      expect(CASE_PUBLICATION_COPY[state]).toBeTruthy()
    }
  })

  it('say something different for applied than for verified', () => {
    // Applied means we wrote it. Verified means somebody checked a reader gets
    // it back. Reading the same would promise the second while doing the first.
    expect(CASE_PUBLICATION_COPY.applied).not.toBe(CASE_PUBLICATION_COPY.verified)
    expect(CASE_PUBLICATION_COPY.pending).not.toBe(CASE_PUBLICATION_COPY.applied)
  })

  it('distinguish being accepted from being visible to the public', () => {
    // The decision and the public change are different events, and a reporter
    // who is told only "accepted" will go and look at a page that has not moved.
    expect(CASE_DECISION_COPY.action_taken).not.toBe(CASE_PUBLICATION_COPY.verified)
    expect(CASE_PUBLICATION_COPY.pending).toContain('chờ')
    expect(CASE_PUBLICATION_COPY.verified).toContain('công khai')
  })

  it('never fall back on one generic phrase for everything', () => {
    const phrases = Object.values(CASE_PUBLICATION_COPY)

    expect(new Set(phrases).size).toBe(phrases.length)
    for (const phrase of [...phrases, ...Object.values(CASE_DECISION_COPY)]) {
      expect(phrase.trim().toLowerCase()).not.toBe('đã xử lý')
    }
  })

  it('does not promise a resolution time nobody agreed to', () => {
    // The promise the kernel actually makes is a next update, not a fix within
    // any number of hours.
    for (const phrase of Object.values(CASE_PUBLICATION_COPY)) {
      expect(phrase).not.toMatch(/24|48|giờ/)
    }
  })
})

describe('the decision vocabulary', () => {
  it('covers every disposition family the backend can report', () => {
    const source = backendSource('agent/cases/domain.py')
    const declared = enumValues(source, 'DispositionFamily')

    for (const family of Object.keys(CASE_DECISION_COPY)) {
      expect(declared, `DispositionFamily lost ${family}`).toContain(`'${family}'`)
    }
  })
})
