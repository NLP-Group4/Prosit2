/**
 * Notarization script for macOS builds
 * 
 * This script is called by electron-builder after signing the app.
 * It submits the app to Apple for notarization (required for macOS 10.15+).
 * 
 * To use this, you need:
 * 1. An Apple Developer account
 * 2. App-specific password for notarization
 * 3. Environment variables set:
 *    - APPLE_ID: Your Apple ID email
 *    - APPLE_ID_PASSWORD: App-specific password
 *    - APPLE_TEAM_ID: Your team ID
 * 
 * For development builds, notarization can be skipped.
 */

const { notarize } = require('@electron/notarize');

exports.default = async function notarizing(context) {
  const { electronPlatformName, appOutDir } = context;
  
  // Only notarize macOS builds
  if (electronPlatformName !== 'darwin') {
    return;
  }

  // Skip if environment variables are not set (development builds)
  if (!process.env.APPLE_ID || !process.env.APPLE_ID_PASSWORD || !process.env.APPLE_TEAM_ID) {
    console.log('Skipping notarization: Apple credentials not found in environment');
    return;
  }

  const appName = context.packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;

  console.log(`Notarizing ${appPath}...`);

  try {
    await notarize({
      appPath,
      appleId: process.env.APPLE_ID,
      appleIdPassword: process.env.APPLE_ID_PASSWORD,
      teamId: process.env.APPLE_TEAM_ID,
    });
    
    console.log('Notarization complete!');
  } catch (error) {
    console.error('Notarization failed:', error);
    throw error;
  }
};
