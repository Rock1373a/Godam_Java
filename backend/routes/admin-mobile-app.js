const express = require('express');
const fs = require('fs');
const path = require('path');
const { resolveApkPath, embeddedApiBaseForDisplay } = require('../utils/mobileApkPath');

const router = express.Router();

router.get('/', (req, res) => {
  try {
    const p = resolveApkPath();
    const embeddedApiBase = embeddedApiBaseForDisplay();
    if (!fs.existsSync(p)) {
      return res.json({
        available: false,
        embeddedApiBase,
        message: 'APK file not found on server. Build with scripts/build-godam-android-release-apk.sh and deploy the artifact.',
      });
    }
    const st = fs.statSync(p);
    return res.json({
      available: true,
      filename: path.basename(p),
      sizeBytes: st.size,
      updatedAt: st.mtime.toISOString(),
      embeddedApiBase,
    });
  } catch (e) {
    return res.status(500).json({ error: e.message || 'Failed to read APK metadata' });
  }
});

router.get('/apk', (req, res) => {
  const p = resolveApkPath();
  if (!fs.existsSync(p)) {
    return res.status(404).json({
      error: 'APK not deployed',
      detail: 'Place the release APK at uploads/mobile/GoDam.apk or set MOBILE_APP_APK_PATH.',
    });
  }
  const name = path.basename(p);
  res.setHeader('Content-Type', 'application/vnd.android.package-archive');
  return res.download(p, name);
});

module.exports = router;
