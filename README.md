# Big Encore Enabler

One-download bundle for Borderlands 4: it includes the BL4 PythonSDK/Mod Manager and this mod.

## Install

1. Close Borderlands 4.
2. Download the latest timestamped `BigEncoreEnabler-Full-Bundle-YYYYMMDD-HHMMSS.zip` from `dist/archives/` and extract its contents into the Borderlands 4 game folder, merging folders if asked.
3. Start the game. The mod is enabled automatically on first install; later enable/disable choices are remembered in the Mods menu.

Tracks loaded Boss Replay machines without changing them at spawn. When the
player enters the 1800-unit proximity radius, the mod enables that machine's
Big Encore state and shows a semi-transparent animated UMG notification with a
title and message. It does not launch fights or change the weekly rotation.
Multiplayer has not been tested.

The notification is intentionally a custom UMG card rather than the inaccessible
Cohtml toast. Its card is petrol-blue and deliberately translucent; the title
and description use separate native `TextBlock` widgets with the game's
`Industry-Demi` and `Industry-Book` faces. The boss name is a third Demi
`TextBlock`, rendered orange immediately before the light ` activated` suffix.
It receives a one-pixel text outline so it reads slightly bolder without
depending on an unverified cooked `Bold` face.
When the cooked Boss Replay gem texture/material is exposed by the live build,
the card also adds three small falling gem passes inside the frame. This layer
is optional and never replaces the normal card if the asset is unavailable.
A one-pixel UMG divider separates the two rows. The renderer first tries the
game's `generic_slideout_background` as a boxed brush to reproduce the blue
slideout gradient and corners, then `online_slideout_background`; if those
textures are not exposed in the live build, it falls back to a nested
translucent coloured UMG frame. The card places the game's own Big Encore icon
at the top-left of the title row: it first looks up the live
`ico_weekly_true_boss_replay` texture, then `ico_boss_replay`, with
currency/online icons as safe fallbacks. Only if none of those cooked assets is
available does it try to import the supplied `bencore_icon.png` through Unreal's
`KismetRenderingLibrary`. The PNG remains included beside the packaged mod as a
last-resort fallback.

For the description name, the mod reads the panel's `BossDisplayName` and
resolves its `FGbxDefPtr` through BL4's `GetTextFromUICharacterName` API. The
internal fight identifier remains the fallback if localization is unavailable.
This is the localized name attached to the loaded station; the server's weekly
True Boss rotation can still expose a different name from the station's static
definition.

## Development testing — no restart required

**Release rule:** after every source edit, rebuild the complete drag-and-drop
full bundle containing `OakGame`, `sdk_mods`, PythonSDK and this mod. On
Windows, run `build_release.ps1`; it updates
`dist/BigEncoreEnabler-Full-Bundle.zip` and creates a timestamped
copy under `dist/archives/` named
`BigEncoreEnabler-Full-Bundle-YYYYMMDD-HHMMSS.zip`.
For a lightweight mod-only archive, run `build_plugin.ps1`; it writes the
corresponding `BigEncoreEnabler-Plugin` files under `dist/` and `dist/archives/`.

**Project rule: test research and UI changes from the live BL4 PythonSDK
console with `pyexec`; do not restart the game for an iteration.** Always use
the complete Windows path; do not rely on a junction or current directory. For
a live proximity test specifically:

```text
pyexec M:\mhawhome\workspace\games\bl4\script\BL4MoxxiProximityNotificationTest.py
```

Run it after the character and HUD are fully loaded. The harness tracks
inactive machines and writes `Script_EligibleForTrueBoss` only when the
player enters the 1800-unit radius, then displays the UMG card. Stop it without
restarting with:

```text
pyexec M:\mhawhome\workspace\games\bl4\script\BL4MoxxiProximityNotificationStop.py
```

The trace is written to
`M:\mhawhome\workspace\games\bl4\traces\bl4-moxxi-proximity-notification.log`.
The packaged mod uses the same renderer and proximity logic automatically.

To reload the modified packaged module in the current session without a game
restart (especially after changing deferred activation), run:

```text
pyexec M:\mhawhome\workspace\games\bl4\script\BL4MoxxiLiveReload.py
```

Use a newly streamed boss-machine area after the reload: panels already loaded
by the previous version may already have their eligibility state set.

To preview the card immediately, without requiring a loaded or nearby
machine, run:

```text
pyexec M:\mhawhome\workspace\games\bl4\script\BL4MoxxiNotificationPreview.py
```

The same stop command removes the preview card and its temporary tick hook.

The proximity harness and the packaged notification are UMG-only and can be
iterated from the current session. Do **not** invoke UI Blueprint handlers such
as loot-feed `AppearEridium` directly with reconstructed widget arguments: their
internal event state is not public API and a direct test crashed BL4.

The proximity registry keeps only stable object-path strings. Streamed actor
objects are resolved afresh for each check and are not retained across HUD
ticks; a missing actor is skipped rather than calling location/state methods on
the BossReplay script object. This prevents an unloaded area from leaving
stale UObjects behind.

## Credits and requirements

The included BL4 SDK release is from the community project [bl-sdk / Oak 2 Mod Manager](https://github.com/bl-sdk/oak2-mod-manager), which provides PythonSDK, `pyunrealsdk`, `unrealsdk`, and `mods_base`. Its release is included for convenience; see `THIRD-PARTY-NOTICES.txt` and the licenses inside `sdk_mods` for upstream credits and terms.

This bundle does not include the Microsoft Visual C++ Redistributable; the official SDK installation guide lists it as a prerequisite. Most Windows gaming PCs already have it installed.
