"""Enable Moxxi’s Big Encore Machine when the player approaches it.

Install by extracting the complete timestamped full bundle into the Borderlands
4 game root. The mod lives under sdk_mods/BigEncoreEnabler; do not install
an old standalone .sdkmod beside it. It enables itself on first install; the
PythonSDK mod menu can disable it later, and mods_base remembers that choice.
The hook tracks each Boss Replay panel at OnBeginPlay, including panels created
later by streamed sublevels, but defers the eligibility state change until the
player enters the proximity radius. A one-time scan also covers panels already
loaded when the mod is enabled. Tracked entries retain only object paths and
resolve live UObjects for the current check, so streamed actors are not kept
alive across ticks. It never starts a fight or changes WeeklyManager/rotation
data.
Multiplayer has not been tested.
"""

from datetime import datetime
from pathlib import Path
from time import monotonic

import unrealsdk
from mods_base import Game, Mod, SETTINGS_DIR, build_mod, hook

from .umg_notification import BigEncoreUmgNotification


TRACE_DIR = Path(r"M:\mhawhome\workspace\games\bl4\traces")
TRACE_FILE = TRACE_DIR / "big-encore-enabler.log"
PANEL_CLASS = "Script_BossReplay_C"
PANEL_PATH_TOKEN = "PersistentLevel.IO_BossReplay_"
ELIGIBILITY_MACHINE = "Script_EligibleForTrueBoss"
HOOK_ID = "big_encore_enabler_on_begin_play"
TICK_HOOK_ID = "big_encore_enabler_proximity_tick"
TICK_PATH = "/Script/GbxUIUMG.GbxUIUMGTickWidget:BP_TickWidget"
MOD_NAME = "Big Encore Enabler"
PROXIMITY_RADIUS = 1800.0
PROXIMITY_RESET_RADIUS = PROXIMITY_RADIUS * 1.35
PROXIMITY_POLL_SECONDS = 0.25

_handled_panels: set[str] = set()
_eligible_panels: dict[str, dict] = {}
_last_proximity_poll = 0.0


def log(message: str) -> None:
    try:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        with TRACE_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


_notification = BigEncoreUmgNotification(log)


def _find_panel_actor(script_path: str):
    """Resolve only the real OakInteractiveObject for a BossReplay path."""
    try:
        actor_path = script_path.split(".Script_BossReplay_C_", 1)[0]
        actor = unrealsdk.find_object("OakInteractiveObject", actor_path)
        if actor is not None and "OakInteractiveObject" in str(actor.Class.Name):
            return actor
    except Exception as exc:
        log(f"ANCHOR direct lookup failed path={script_path}: {exc!r}")
    return None


def _panel_actor_path(script_path: str) -> str:
    return script_path.split(".Script_BossReplay_C_", 1)[0]


def _resolve_live_anchor(entry):
    """Resolve only a currently live actor; never retain a streamed UObject."""
    actor_path = entry.get("actor_path")
    if actor_path:
        try:
            actor = unrealsdk.find_object("OakInteractiveObject", actor_path)
            if actor is not None and "OakInteractiveObject" in str(actor.Class.Name):
                return actor
        except Exception:
            pass

    return None


def _remember_panel(
    script,
    script_path: str,
    fight_name: str,
    display_name: str,
    actor,
    activated: bool,
) -> None:
    """Track a loaded machine without changing its eligibility state."""
    actor_path = _panel_actor_path(script_path)
    existing = _eligible_panels.get(script_path)
    if existing is not None:
        existing["script_path"] = script_path
        existing["actor_path"] = actor_path
        existing["fight_name"] = fight_name
        existing["display_name"] = display_name
        existing["activated"] = bool(existing.get("activated") or activated)
        return

    _eligible_panels[script_path] = {
        "script_path": script_path,
        "actor_path": actor_path,
        "fight_name": fight_name,
        "display_name": display_name,
        "activated": bool(activated),
        "inside": False,
        "notified": False,
    }
    log(
        f"PANEL_TRACKED fight={fight_name!r} activated={bool(activated)} "
        f"panel={script_path} actor_path={actor_path}"
    )


def _local_pawn():
    try:
        controllers = [
            pc for pc in unrealsdk.find_all("PlayerController", exact=False)
            if "default__" not in pc._path_name().lower()
        ]
    except Exception as exc:
        log(f"PROXIMITY controller scan failed: {exc!r}")
        return None
    for controller in controllers:
        try:
            pawn = controller.Pawn
            if pawn is not None:
                return pawn
        except Exception:
            continue
    return None


def _location(obj):
    try:
        return obj.K2_GetActorLocation()
    except Exception:
        try:
            return obj.GetActorLocation()
        except Exception:
            return None


def _distance_squared(left, right):
    try:
        dx = float(left.X) - float(right.X)
        dy = float(left.Y) - float(right.Y)
        dz = float(left.Z) - float(right.Z)
        return dx * dx + dy * dy + dz * dz
    except Exception:
        return None


def _state_access(actor):
    if actor is None:
        return None
    try:
        if "OakInteractiveObject" not in str(actor.Class.Name):
            log(f"STATE ACCESS SKIP non-actor owner={getattr(actor, '_path_name', lambda: repr(actor))()}")
            return None
        library = unrealsdk.find_object(
            "GbxActorStateBlueprintLibrary",
            "/Script/GbxEngine.Default__GbxActorStateBlueprintLibrary",
        )
        if library is None:
            return None
        key = unrealsdk.make_struct(
            "GbxActorStateMachineKey", Name=ELIGIBILITY_MACHINE, Index=-1
        )
        return library, key
    except Exception as exc:
        log(f"STATE ACCESS ERROR actor={getattr(actor, '_path_name', lambda: repr(actor))()} error={exc!r}")
        return None


def _read_eligibility(actor):
    access = _state_access(actor)
    if access is None:
        return None
    library, key = access
    try:
        result = library.GetActorStateAsBool(actor, key)
    except Exception as exc:
        log(f"STATE READ ERROR actor={getattr(actor, '_path_name', lambda: repr(actor))()} error={exc!r}")
        return None
    if not (isinstance(result, tuple) and result and isinstance(result[0], bool)):
        log(f"STATE READ UNEXPECTED actor={getattr(actor, '_path_name', lambda: repr(actor))()} result={result!r}")
        return None
    return bool(result[0]), library, key


def _activate_panel(panel_path: str, entry: dict) -> str:
    """Enable one tracked panel after the player enters its radius."""
    if entry.get("activated"):
        log(f"ALREADY_ENABLED_CACHED panel={panel_path}")
        return "already"
    actor = _find_panel_actor(entry.get("actor_path", _panel_actor_path(panel_path)))
    state = _read_eligibility(actor)
    if state is None:
        log(f"DEFERRED_ACTIVATION_UNAVAILABLE panel={panel_path}")
        return "unavailable"

    before, library, key = state
    if before:
        entry["activated"] = True
        log(f"ALREADY_ENABLED panel={panel_path}")
        return "already"

    try:
        setter_result = library.SetActorStateAsBool(actor, key, True)
        after_result = library.GetActorStateAsBool(actor, key)
    except Exception as exc:
        log(f"ACTIVATION ERROR panel={panel_path} error={exc!r}")
        return "failed"

    if not (isinstance(after_result, tuple) and after_result
            and isinstance(after_result[0], bool)):
        log(
            f"ACTIVATION READBACK UNEXPECTED panel={panel_path} "
            f"result={after_result!r} setter={setter_result!r}"
        )
        return "failed"
    if not after_result[0]:
        log(
            f"ACTIVATION FAILED panel={panel_path} before={before} "
            f"after={after_result!r} setter={setter_result!r}"
        )
        return "failed"

    entry["activated"] = True
    log(
        f"ACTIVATED_ON_PROXIMITY panel={panel_path} before={before} "
        f"after=True setter={setter_result!r}"
    )
    return "activated"


def _text_value(value) -> str:
    """Convert a reflected FText-like return value to displayable text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    for method_name in ("ToString", "to_string", "GetString"):
        try:
            method = getattr(value, method_name, None)
            if callable(method):
                rendered = method()
                if rendered is not None:
                    text = str(rendered).strip()
                    if text:
                        return text
        except Exception:
            continue
    try:
        return str(value).strip()
    except Exception:
        return ""


def _resolve_display_name(script, fallback: str) -> str:
    """Resolve BossDisplayName's FGbxDefPtr through BL4's localized-text API."""
    try:
        ui_name = script.BossDisplayName
    except Exception as exc:
        log(f"DISPLAY NAME READ ERROR fallback={fallback!r} error={exc!r}")
        return fallback
    if ui_name is None:
        return fallback

    sources = []
    try:
        fight = script.BossFightInfo
        if fight is not None:
            sources.append(("fight", fight))
    except Exception:
        pass
    try:
        statics = unrealsdk.find_object(
            "OakBossStatics", "/Script/OakGame.Default__OakBossStatics"
        )
        if statics is not None:
            sources.append(("statics", statics))
    except Exception:
        pass

    for source_name, source in sources:
        try:
            resolver = getattr(source, "GetTextFromUICharacterName", None)
            if resolver is None:
                continue
            result = resolver(ui_name)
            display = _text_value(result)
            if display and display != repr(result):
                log(
                    f"DISPLAY NAME RESOLVED source={source_name} "
                    f"reference={ui_name!r} display={display!r}"
                )
                return display
            log(
                f"DISPLAY NAME EMPTY source={source_name} "
                f"reference={ui_name!r} result={result!r}"
            )
        except Exception as exc:
            log(
                f"DISPLAY NAME RESOLVE ERROR source={source_name} "
                f"reference={ui_name!r} error={exc!r}"
            )
    log(f"DISPLAY NAME FALLBACK reference={ui_name!r} fallback={fallback!r}")
    return fallback


def _show_proximity_notification(
    fight_name: str, display_name: str, distance: float
) -> None:
    body = " activated"
    try:
        _notification.show("Moxxi's Big Encore", body, accent=display_name)
        log(
            f"PROXIMITY_NOTIFICATION_SHOWN fight={fight_name!r} "
            f"display={display_name!r} "
            f"distance={distance:.1f} radius={PROXIMITY_RADIUS:.1f}"
        )
    except Exception as exc:
        log(f"PROXIMITY_NOTIFICATION_ERROR fight={fight_name!r} error={exc!r}")


def _proximity_poll() -> None:
    """Activate and announce a tracked machine when the player gets close."""
    global _last_proximity_poll
    now = monotonic()
    if now - _last_proximity_poll < PROXIMITY_POLL_SECONDS:
        _notification.tick()
        return
    _last_proximity_poll = now
    _notification.tick()
    if not _eligible_panels:
        return

    pawn = _local_pawn()
    player_location = _location(pawn) if pawn is not None else None
    if player_location is None:
        return

    for panel_path, entry in list(_eligible_panels.items()):
        anchor = _resolve_live_anchor(entry)
        target_location = _location(anchor) if anchor is not None else None
        if target_location is None:
            continue
        distance_squared = _distance_squared(player_location, target_location)
        if distance_squared is None:
            continue
        distance = distance_squared ** 0.5
        if distance <= PROXIMITY_RADIUS:
            if not entry.get("inside"):
                entry["inside"] = True
                if not entry.get("notified"):
                    activation = _activate_panel(panel_path, entry)
                    if activation == "activated":
                        entry["notified"] = True
                        _show_proximity_notification(
                            str(entry.get("fight_name", "Big Encore")),
                            str(entry.get("display_name") or entry.get("fight_name", "Big Encore")),
                            distance,
                        )
                    elif activation == "already":
                        entry["notified"] = True
                        log(f"PROXIMITY_NOTIFICATION_SKIPPED_ALREADY_ENABLED panel={panel_path}")
        elif distance > PROXIMITY_RESET_RADIUS:
            entry["inside"] = False
            entry["notified"] = False


def track_panel(script) -> None:
    """Track one initialized machine; activation is deferred to proximity."""
    try:
        if str(script.Class.Name) != PANEL_CLASS:
            return
        script_path = script._path_name()
        if PANEL_PATH_TOKEN not in script_path:
            return

        fight = script.BossFightInfo
        if fight is None:
            log(f"SKIP no BossFightInfo: {script_path}")
            return

        fight_name = str(fight.GetBossFightName())
        display_name = _resolve_display_name(script, fight_name)
        fight_state = repr(fight.GetBossFightState())
        if "Inactive" not in fight_state:
            log(f"SKIP fight not inactive ({fight_name}; {fight_state}): {script_path}")
            return

        # The same panel can be seen by the initial scan and the BeginPlay
        # hook.  It is still useful to refresh the proximity anchor when the
        # streamed actor has just finished initialization.
        if script_path in _handled_panels:
            if script_path not in _eligible_panels:
                actor = _find_panel_actor(script_path)
                state = _read_eligibility(actor)
                _remember_panel(
                    script,
                    script_path,
                    fight_name,
                    display_name,
                    actor,
                    bool(state and state[0]),
                )
            return

        actor = _find_panel_actor(script_path)
        state = _read_eligibility(actor)
        activated = bool(state and state[0])
        _handled_panels.add(script_path)
        _remember_panel(
            script, script_path, fight_name, display_name, actor, activated
        )
        if state is None:
            log(f"DEFERRED {fight_name}: state unavailable; panel={script_path}")
        elif activated:
            log(f"TRACKED_ALREADY_ENABLED {fight_name}: panel={script_path}")
        else:
            log(f"DEFERRED {fight_name}: activation waits for radius={PROXIMITY_RADIUS:.1f}; panel={script_path}")
    except Exception as exc:
        try:
            path = script._path_name()
        except Exception:
            path = repr(script)
        log(f"ERROR {exc!r}; panel={path}")


@hook(
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Script_BossReplay.Script_BossReplay_C:OnBeginPlay",
    unrealsdk.hooks.Type.POST,
    hook_identifier=HOOK_ID,
)
def on_boss_replay_begin_play(obj, args, ret, func):
    """Called after each Boss Replay panel's Blueprint initialization."""
    track_panel(obj)


def scan_loaded_panels() -> None:
    """Cover panels that were already initialized before the mod was enabled."""
    count = 0
    try:
        # Blueprint-generated classes may not resolve by short name through
        # find_all(), so use the same broad UObject enumeration as the probes.
        for script in unrealsdk.find_all("Object", exact=False):
            try:
                if (str(script.Class.Name) == PANEL_CLASS
                        and PANEL_PATH_TOKEN in script._path_name()):
                    count += 1
                    track_panel(script)
            except Exception as exc:
                log(f"SCAN ERROR {exc!r}")
    except Exception as exc:
        log(f"SCAN FAILED {exc!r}")
        return
    log(f"Initial scan complete: {count} loaded Boss Replay panel(s)")


@hook(TICK_PATH, unrealsdk.hooks.Type.POST, hook_identifier=TICK_HOOK_ID)
def on_umg_tick(obj, args, ret, func):
    """Drive the throttled proximity check and the notification animation."""
    _proximity_poll()


def on_enable() -> None:
    log("MOD ENABLED; registering boss machine initialization hook and scanning loaded machines")
    log(
        f"PROXIMITY notification armed radius={PROXIMITY_RADIUS:.1f} "
        f"poll={PROXIMITY_POLL_SECONDS:.2f}s"
    )
    scan_loaded_panels()


def on_disable() -> None:
    _notification.cleanup("mod disabled")
    _eligible_panels.clear()
    _handled_panels.clear()
    log("MOD DISABLED; future panel initializations will not be changed")


class EnableOnFirstInstall(Mod):
    """Default to enabled once; afterwards respect the user's saved menu choice."""

    def load_settings(self) -> None:
        settings_file = self.settings_file
        first_install = settings_file is not None and not settings_file.exists()
        super().load_settings()
        if first_install and not self.enabling_locked and not self.is_enabled:
            self.enable()


MOD = build_mod(
    cls=EnableOnFirstInstall,
    name=MOD_NAME,
    author="Codex",
    description=(
        "Automatically enables Moxxi’s Big Encore Machine at loaded boss machines, "
        "including streamed areas, and shows a proximity UMG notification. "
        "Multiplayer has not been tested."
    ),
    version="2.5.0",
    supported_games=Game.BL4,
    settings_file=SETTINGS_DIR / "big_encore_enabler.json",
    hooks=[on_boss_replay_begin_play, on_umg_tick],
    on_enable=on_enable,
    on_disable=on_disable,
    auto_enable=True,
)
