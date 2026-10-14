# Mealie Health bridge (iOS 17+)

Minimal SwiftUI companion, one personal Mealie account per installation. Read-only HealthKit access.
No recipe database or third-party analytics. Build/sign/install with your own Apple developer account.
**Source supplied; an Xcode build and physical-device acceptance test remain required.** This Linux environment cannot certify them.

## Build

1. On a Mac install Xcode and XcodeGen (`brew install xcodegen`).
2. In `project.yml` replace `com.example.MealieHealth` with your unique registered bundle ID. Set your development team in Xcode.
3. Run `xcodegen generate`, open `MealieHealth.xcodeproj`, select your team and an iPhone.
4. Enable HealthKit and Background Delivery in Signing & Capabilities. Verify the generated entitlements and purpose text.
5. Run on each person's own iPhone. Private developer installation or TestFlight is sufficient; App Store publication is optional.
6. Enter your HTTPS Mealie URL and your **own** API token, choose Health permissions and tap Sync.

No credentials, signing certificates or actual health records belong in Git. Use separate Mealie accounts in a shared household.
The app accepts HTTPS only, rejects redirects and stores credentials and sync anchors in the device-only Keychain.
You still need a reachable server and valid certificate; no VPS deployment was performed with this change.

## Data and deletion

- Weight, height and optional body fat: actual HealthKit samples from the last 90 days.
- Workouts: duration from the last 90 days; no route, heart-rate series or location upload.
- Steps and active/resting energy: reconciled daily HealthKit statistics for the last 28 days.
  Never sum overlapping Watch/iPhone raw samples and never add active energy again to an activity-factor estimate.
- Sample UUIDs and daily keys make retries upserts. Revision conflicts reload and retry up to three times.
- Anchored queries recognize actual deleted weight/height/fat/workout samples; anchors advance only after successful server sync.
  Missing/denied reads are never inferred to mean deletion or zero intake.
- Daily statistics are refreshed when available. If an entire day disappears or access is revoked, a previous daily aggregate
  may remain; use **Delete synced data and disconnect** to remove the server copy. This is deliberately conservative.
- Delete clears measurements and derived goal history for this account; the separately entered planning profile remains.
- Disconnect stops observers and removes local credentials/anchors. Revoke Health access in iOS settings and API tokens in Mealie.
- Background delivery is best effort, not a schedule guarantee. Open the app and sync before a monthly review.
- Age, activity assumptions, exclusions and agreed protein reference weight are entered in Mealie; birth date is not read from HealthKit.

## Device acceptance checklist

Test independently with two accounts and synthetic data before real measurements:

- Allow weight only, then partial/full denial; no fabricated zero readings or deletion on denial.
- Sync twice; the same samples do not duplicate. Edit/delete a weight in Health and verify reconciliation.
- Disconnect/reconnect and switch accounts; no upload to the former account or another household.
- Change the editable server field during sync; requests still use the committed connection.
- Network loss midway through batches; retry safely without advancing anchors early.
- Check combined Watch/phone daily totals against the Health app, timezone changes and midnight boundaries.
- Delete synced data; verify raw observations and derived proposals are absent on the server.
- Verify observer completion, foreground resume, locked-device behavior and background delivery on a physical iPhone.

A public App Store release additionally needs an app icon, signed archive, privacy policy, accurate App Privacy disclosure,
review metadata and device testing. These are deployment/distribution work, not a claim that this source is already published.
