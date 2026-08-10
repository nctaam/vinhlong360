[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [PSCustomObject]$Settings
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$flagSetting = @($Settings.settings | Where-Object key -eq 'features.flags') | Select-Object -First 1
if ($null -eq $flagSetting -or $null -eq $flagSetting.value) {
  throw 'features.flags is missing from the site settings response'
}

$flags = @{}
$flagSetting.value.PSObject.Properties | ForEach-Object {
  $flags[$_.Name] = $_.Value
}

@(
  'public_personalization_v1'
  'public_recommendation_v1'
  'public_search_expansion_v1'
  'public_optimizer_v1'
  'public_proactive_notices_v1'
) | ForEach-Object {
  $flags[$_] = $false
}

@{ value = $flags } | ConvertTo-Json -Depth 6 -Compress
