/**
 * SSR Reproduction Script for Cognitive Terroir Engine
 * Challenger: challenger_m2_1_10
 *
 * Demonstrates the SSR defect where detectNetworkCondition() returns isOffline=true in Node.js
 */

import { detectNetworkCondition, useCognitiveTerroir } from '../composables/useCognitiveTerroir.ts'

console.log('--- Headless Node.js SSR Environment Check ---')
console.log('typeof window:', typeof window)
console.log('typeof navigator:', typeof navigator)
console.log('navigator.onLine:', typeof navigator !== 'undefined' ? navigator.onLine : 'N/A')

const net = detectNetworkCondition()
console.log('\n--- detectNetworkCondition() Result ---')
console.log(JSON.stringify(net, null, 2))

const terroir = useCognitiveTerroir()
console.log('\n--- useCognitiveTerroir() Reactive States ---')
console.log('isOffline:', terroir.isOffline.value)
console.log('isFieldMode:', terroir.isFieldMode.value)
console.log('network.profile:', terroir.network.value.profile)

if (net.isOffline === true || terroir.isOffline.value === true) {
  console.error('\n[DEFECT CONFIRMED]: SSR falsely evaluated environment as OFFLINE!')
  process.exit(1)
} else {
  console.log('\n[PASS]: SSR correctly evaluated environment as ONLINE.')
  process.exit(0)
}
