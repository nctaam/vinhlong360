export function useSeasonTheme() {
  const month = new Date().getMonth() + 1
  let cls: string
  if (month <= 2) cls = 'season-tet'
  else if (month <= 6) cls = 'season-he'
  else if (month <= 11) cls = 'season-nuoc'
  else cls = 'season-thu'

  useHead({ htmlAttrs: { class: cls } })
}
