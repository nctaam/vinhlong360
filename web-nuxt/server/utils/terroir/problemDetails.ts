import { setResponseHeader, setResponseStatus, type H3Event } from 'h3'

export interface InvalidParamDetail {
  readonly name: string
  readonly reason: string
}

export interface ProblemDetailsPayload {
  readonly type: string
  readonly title: string
  readonly status: number
  readonly detail: string
  readonly instance: string
  readonly code: string
  readonly invalid_params?: readonly InvalidParamDetail[]
  readonly timestamp: string
}

export function sendProblemDetails(
  event: H3Event,
  options: {
    status: number
    type: string
    title: string
    detail: string
    code: string
    invalidParams?: readonly InvalidParamDetail[]
  },
): ProblemDetailsPayload {
  const reqUrl = event.node?.req?.url || event.path || '/api/v1/terroir'
  const payload: ProblemDetailsPayload = {
    type: options.type,
    title: options.title,
    status: options.status,
    detail: options.detail,
    instance: reqUrl,
    code: options.code,
    ...(options.invalidParams ? { invalid_params: options.invalidParams } : {}),
    timestamp: new Date().toISOString(),
  }

  setResponseStatus(event, options.status)
  setResponseHeader(event, 'Content-Type', 'application/problem+json; charset=utf-8')
  setResponseHeader(event, 'Cache-Control', 'no-store, no-cache, must-revalidate')
  return payload
}
