import type { JsonValue, ProjectAsset } from '@/types/project'

export interface ProjectVideo {
  kind: 'youtube' | 'file'
  url: string
  title: string
  credits: string
}

function metadataString(metadata: Record<string, JsonValue>, keys: string[]): string {
  for (const key of keys) {
    const value = metadata[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function youtubeEmbedUrl(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl)
    const hostname = url.hostname.toLowerCase().replace(/^www\./, '')
    let videoId = ''

    if (hostname === 'youtu.be') {
      videoId = url.pathname.split('/').filter(Boolean)[0] || ''
    } else if (hostname === 'youtube.com' || hostname === 'youtube-nocookie.com') {
      if (url.pathname === '/watch') videoId = url.searchParams.get('v') || ''
      else if (/^\/(embed|shorts)\//.test(url.pathname)) videoId = url.pathname.split('/')[2] || ''
    }

    return /^[A-Za-z0-9_-]{11}$/.test(videoId)
      ? `https://www.youtube-nocookie.com/embed/${videoId}`
      : null
  } catch {
    return null
  }
}

function directVideoUrl(rawUrl: string): string | null {
  if (!rawUrl.trim()) return null
  try {
    const isAbsolute = /^[a-z][a-z\d+.-]*:/i.test(rawUrl)
    if (!isAbsolute && !rawUrl.startsWith('/uploads/')) return null
    const url = new URL(rawUrl, 'http://localhost')
    if (!['http:', 'https:'].includes(url.protocol) || !/\.(mp4|webm|mov|ogg)$/i.test(url.pathname)) {
      return null
    }
    return isAbsolute ? url.toString() : `${url.pathname}${url.search}${url.hash}`
  } catch {
    return null
  }
}

function isVideoAsset(asset: ProjectAsset): boolean {
  const type = asset.type.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  return type.includes('video') || type.includes('clip')
}

export function resolveProjectVideo(assets: ProjectAsset[]): ProjectVideo | null {
  const candidates = assets
    .filter(isVideoAsset)
    .sort((left, right) => Number(right.featuredRoster) - Number(left.featuredRoster))

  for (const asset of candidates) {
    const youtubeUrl = metadataString(asset.metadata, ['youtube_url', 'youtubeUrl'])
    const embedUrl = youtubeEmbedUrl(youtubeUrl || asset.url)
    if (embedUrl) {
      return {
        kind: 'youtube',
        url: embedUrl,
        title: asset.titre,
        credits: metadataString(asset.metadata, ['realisateur', 'Réalisateur', 'credits'])
      }
    }

    const fileUrl = directVideoUrl(asset.url)
    if (fileUrl) {
      return {
        kind: 'file',
        url: fileUrl,
        title: asset.titre,
        credits: metadataString(asset.metadata, ['realisateur', 'Réalisateur', 'credits'])
      }
    }
  }

  return null
}