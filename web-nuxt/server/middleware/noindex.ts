// Site-wide noindex guard.
//
// While runtimeConfig.public.siteNoindex is true, every response carries
// `X-Robots-Tag: noindex, follow`, keeping the whole site out of Google's index
// during the content-hardening phase. The HTTP header is authoritative: it
// overrides any per-page robots meta (Google applies the most restrictive), and
// it is evaluated per request so toggling the flag needs no rebuild.
//
// Turn indexing back on by setting NUXT_PUBLIC_SITE_NOINDEX=false and restarting.
// robots.txt is intentionally left crawl-allowed so Googlebot can actually fetch
// pages and read this header (a robots.txt Disallow would hide the noindex and
// let URLs linger in the index).
export default defineEventHandler((event) => {
  if (useRuntimeConfig(event).public.siteNoindex) {
    setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')
  }
})
