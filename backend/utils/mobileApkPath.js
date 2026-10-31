const path = require('path');

function resolveApkPath() {
  const custom = process.env.MOBILE_APP_APK_PATH && String(process.env.MOBILE_APP_APK_PATH).trim();
  if (custom) {
    return path.isAbsolute(custom) ? custom : path.resolve(__dirname, '..', custom);
  }
  return path.resolve(__dirname, '..', 'uploads', 'mobile', 'GoDam.apk');
}

function embeddedApiBaseForDisplay() {
  const raw =
    process.env.MOBILE_APP_EMBEDDED_API_BASE ||
    process.env.EXPO_PUBLIC_API_URL ||
    process.env.PUBLIC_API_ORIGIN ||
    '';
  const t = String(raw).trim().replace(/\/+$/, '');
  if (!t) return '';
  if (/\/api$/i.test(t)) return t;
  try {
    const u = new URL(t.includes('://') ? t : `https://${t}`);
    if (u.protocol !== 'http:' && u.protocol !== 'https:') return '';
    return `${u.origin}/api`;
  } catch {
    return '';
  }
}

module.exports = { resolveApkPath, embeddedApiBaseForDisplay };
