const express = require('express');
const fs = require('fs');
const path = require('path');
const { resolveApkPath, embeddedApiBaseForDisplay } = require('../utils/mobileApkPath');

const router = express.Router();

/**
 * Public metadata (no auth). Use with GET …/public/apk for anonymous install links.
 */
router.get('/info', (req, res) => {
  try {
    const apkPath = resolveApkPath();
    const embeddedApiBase = embeddedApiBaseForDisplay();
    if (!fs.existsSync(apkPath)) {
      return res.json({
        available: false,
        embeddedApiBase,
        message: 'APK file not found on server.',
      });
    }
    const st = fs.statSync(apkPath);
    return res.json({
      available: true,
      filename: path.basename(apkPath),
      sizeBytes: st.size,
      updatedAt: st.mtime.toISOString(),
      embeddedApiBase,
    });
  } catch (e) {
    return res.status(500).json({ error: e.message || 'Failed to read APK metadata' });
  }
});

/**
 * Public APK download (no auth). Same file as admin route; use when you want a shareable link.
 */
router.get('/apk', (req, res) => {
  if (process.env.MOBILE_APP_DISABLE_PUBLIC_APK === '1') {
    return res.status(404).json({ error: 'Public APK download is disabled (MOBILE_APP_DISABLE_PUBLIC_APK=1).' });
  }
  const apkPath = resolveApkPath();
  if (!fs.existsSync(apkPath)) {
    return res.status(404).json({
      error: 'APK not deployed',
      detail: 'Place the release APK at uploads/mobile/GoDam.apk or set MOBILE_APP_APK_PATH.',
    });
  }
  const name = path.basename(apkPath);
  res.setHeader('Content-Type', 'application/vnd.android.package-archive');
  return res.download(apkPath, name);
});

module.exports = router;
