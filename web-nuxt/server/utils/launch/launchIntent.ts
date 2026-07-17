export type LaunchIntent =
  | { readonly openIntent: false; readonly reason: 'closed-default' | 'invalid-configuration' | 'owner-approval-missing' }
  | { readonly openIntent: true; readonly reason: 'valid-two-key-unlock' }

export function readLaunchIntent(env: NodeJS.ProcessEnv): LaunchIntent {
  const mode = env.LAUNCH_INDEXING_MODE
  const owner = env.LAUNCH_INDEXING_OWNER_APPROVED

  if (mode === undefined && owner === undefined) {
    return { openIntent: false, reason: 'closed-default' }
  }
  if (mode !== 'selective-open') {
    return { openIntent: false, reason: 'invalid-configuration' }
  }
  if (owner !== 'true') {
    return { openIntent: false, reason: 'owner-approval-missing' }
  }
  return { openIntent: true, reason: 'valid-two-key-unlock' }
}
