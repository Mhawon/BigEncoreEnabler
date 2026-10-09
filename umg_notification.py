"""Proven UMG notification renderer for the Moxxi Big Encore mod.

This intentionally mirrors the previously working live test:
TextBlock(s) -> VerticalBox -> Border -> WBP_Primary_Layout
GbxUIUMGOverlay -> BP_TickWidget.
No Cohtml, texture import, viewport reparenting, or experimental UMG layout
classes are involved in this baseline renderer.
"""

from collections import deque
from math import sin
from pathlib import Path
from time import monotonic

import unrealsdk


TEXT_CLASS_PATHS = (
    "/Script/UMG.TextBlock",
    "/Script/GbxUIUMG.GbxUIUMGTextBlock",
)
CARD_CLASS_PATHS = (
    "/Script/UMG.Border",
    "/Script/CommonUI.CommonBorder",
)
VERTICAL_CLASS_PATHS = (
    "/Script/UMG.VerticalBox",
    "/Script/GbxUIUMG.GbxUIUMGVerticalBox",
)
HORIZONTAL_CLASS_PATHS = (
    "/Script/UMG.HorizontalBox",
    "/Script/GbxUIUMG.GbxUIUMGHorizontalBox",
)
OVERLAY_CLASS_PATHS = (
    "/Script/UMG.Overlay",
    "/Script/GbxUIUMG.GbxUIUMGOverlay",
)
SIZEBOX_CLASS_PATHS = (
    "/Script/UMG.SizeBox",
    "/Script/GbxUIUMG.GbxUIUMGSizeBox",
)
TICK_PATH = "/Script/GbxUIUMG.GbxUIUMGTickWidget:BP_TickWidget"

TITLE = "Moxxi's Big Encore"
BODY = "Machine Big Encore activée !"
TOKEN = "MoxxiBigEncoreProximityNotification"
ANIM_IN = 0.35
ANIM_HOLD = 4.55
ANIM_OUT = 0.85
LIFETIME = ANIM_IN + ANIM_HOLD + ANIM_OUT
SLIDE_DISTANCE = 180.0
# Small counter-clockwise tilt matching the reference card.  The pivot is set
# to the center of the complete toast so the title/icon do not shear apart.
TOAST_ROTATION_DEGREES = 0.0
# Keep the card at the vertical center of the live HUD instead of the
# bottom-right safe-area band.  The overlay slot performs this responsively,
# so the card does not drift into a different UI layer at other resolutions.
TOAST_VERTICAL_ALIGNMENT = "VAlign_Center"

# Reference-matched visual pass.  The alpha belongs to the card itself; the
# animation opacity is kept separate so a fade never changes the palette.
# Dark navy/teal pass matching image copy 2.png.  The higher alpha keeps the
# game world from bleaching the gradient through the translucent card.
CARD_BACKGROUND = (0.01, 0.07, 0.12, 0.45)
CARD_TEXTURE_TINT = (0.10, 0.24, 0.34, 0.72)
CARD_FRAME = (0.44, 0.72, 0.82, 0.72)
# Textured dividers must start from neutral white.  Any blue/alpha tint here
# desaturates the cooked orange/blue pixels before Slate draws the brush.
DIVIDER_COLOR = (1.0, 1.0, 1.0, 1.0)
DIVIDER_ACCENT = (0.52, 0.18, 0.015, 0.98)
DIVIDER_ACCENT_WIDTH = 10.0
DIVIDER_EDGE_GAP = 3.0
TITLE_COLOR = (0.95, 0.97, 0.99, 1.0)
BODY_COLOR = (0.70, 0.79, 0.84, 1.0)
ACCENT_COLOR = (1.0, 0.43, 0.06, 1.0)
# The live build exposes the known-good Industry ``Demi`` face, but does not
# prove that a separate ``Bold`` typeface is cooked.  A one-pixel outline makes
# the boss name visibly heavier while preserving the same validated glyphs.
ACCENT_OUTLINE_SIZE = 1
FONT_OBJECT_PATH = "/Game/Fonts/Industry.Industry"
IMAGE_CLASS_PATHS = (
    "/Script/GbxUIUMG.GbxUIUMGImage",
    "/Script/UMG.Image",
)
# These are real cooked Texture2D objects observed in BL4's live object dump.
# The weekly True Boss icon is the closest match to the Moxxi/Big Encore panel;
# keep the generic Boss Replay icon as the second choice. Currency and online
# icons remain safe fallbacks for builds that stream discovery assets later.
ICON_TEXTURE_PATHS = (
    "/Game/uiresources/_shared/assets/ico_ui_art_discovery/ico_weekly_true_boss_replay.ico_weekly_true_boss_replay",
    "/Game/uiresources/_shared/assets/ico_ui_art_discovery/ico_boss_replay.ico_boss_replay",
    "/Game/uiresources/_shared/assets/ico_ui_art_currency/ico_ui_art_currency_eridium.ico_ui_art_currency_eridium",
    "/Game/uiresources/_shared/assets/ico_ui_art_currency/ico_ui_art_currency_money.ico_ui_art_currency_money",
    "/Game/uiresources/online_message/assets/ui_art_assets/online_msg_icon.online_msg_icon",
)
ICON_FILE_NAME = "bencore_icon.png"
ICON_WORKSPACE_PATH = Path(
    r"M:\mhawhome\workspace\games\bl4\bencore_icon.png"
)
# The extra crystal/gem pass used by the physical Boss Replay panel is cooked
# as an FX texture/material rather than a normal UMG icon.  Try both forms and
# the common cooked folder variants; a failed lookup simply leaves the card's
# existing icon and frame unchanged.
GEM_TEXTURE_PATHS = (
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Textures/T_FX_BossReplay_Gems_v04.T_FX_BossReplay_Gems_v04",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Textures/T_FX_BossReplay_Gems_v04",
    "/Game/FX/Systems/BossReplay/t_fx_bossreplay_gems_v04.t_fx_bossreplay_gems_v04",
    "/Game/FX/Systems/BossReplay/t_fx_bossreplay_gems_v04",
    "/Game/FX/Systems/BossReplay/Textures/t_fx_bossreplay_gems_v04.t_fx_bossreplay_gems_v04",
    "/Game/FX/Systems/BossReplay/Textures/t_fx_bossreplay_gems_v04",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/t_fx_bossreplay_gems_v04.t_fx_bossreplay_gems_v04",
)
GEM_MATERIAL_PATHS = (
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Materials/M_FX_Systems_BossReplay_Gems_v02.M_FX_Systems_BossReplay_Gems_v02",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Materials/M_FX_Systems_BossReplay_Gems_v02",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Materials/MI_FX_Systems_BossReplay_Gems_v02_Inst_01.MI_FX_Systems_BossReplay_Gems_v02_Inst_01",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Materials/MI_FX_Systems_BossReplay_Gems_v02_Inst_02.MI_FX_Systems_BossReplay_Gems_v02_Inst_02",
    "/Game/InteractiveObjects/GameSystemMachines/BossReplay/Effects/Materials/MI_FX_Systems_BossReplay_Gems_v02_Inst_03.MI_FX_Systems_BossReplay_Gems_v02_Inst_03",
    "/Game/FX/Systems/BossReplay/m_fx_systems_bossreplay_gems_v02.m_fx_systems_bossreplay_gems_v02",
    "/Game/FX/Systems/BossReplay/m_fx_systems_bossreplay_gems_v02",
    "/Game/FX/Systems/BossReplay/Materials/m_fx_systems_bossreplay_gems_v02.m_fx_systems_bossreplay_gems_v02",
    "/Game/FX/Systems/BossReplay/Materials/m_fx_systems_bossreplay_gems_v02",
    "/Game/FX/Systems/BossReplay/mi_fx_systems_bossreplay_gems_v02_inst_01.mi_fx_systems_bossreplay_gems_v02_inst_01",
    "/Game/FX/Systems/BossReplay/mi_fx_systems_bossreplay_gems_v02_inst_01",
)
CORNER_TEXTURE_PATHS = (
    "/Game/uiresources/ingame_message/assets/ui_art_asset/generic_slideout_background.generic_slideout_background",
    "/Game/uiresources/ingame_message/assets/ui_art_asset/generic_slideout_background",
    "/Game/UIResources/ingame_message/assets/ui_art_asset/generic_slideout_background.generic_slideout_background",
    "/Game/UIResources/ingame_message/assets/ui_art_asset/generic_slideout_background",
    "/Game/uiresources/online_message/assets/ui_art_assets/online_slideout_background",
    "/Game/uiresources/online_message/assets/ui_art_assets/online_slideout_background.online_slideout_background",
    "/Game/UIResources/online_message/assets/ui_art_assets/online_slideout_background",
    "/Game/UIResources/online_message/assets/ui_art_assets/online_slideout_background.online_slideout_background",
)
# This is the same 9-slice separator used by the game's tooltip/dialog UI.
# Do not use celebratory_notifications/Details_DividingLine here: that asset is
# a decorative five-segment strip (orange-blue-orange-blue-orange), not a
# stretchable separator for this card.
DIVIDER_TEXTURE_PATHS = (
    "/Game/uiresources/_shared/assets/ui_art_tool_tip_assets/separator_separator_9slice.separator_separator_9slice",
    "/Game/uiresources/_shared/assets/ui_art_tool_tip_assets/separator_separator_9slice",
    "/Game/UIResources/_shared/assets/ui_art_tool_tip_assets/separator_separator_9slice.separator_separator_9slice",
    "/Game/UIResources/_shared/assets/ui_art_tool_tip_assets/separator_separator_9slice",
)
TITLE_FONT = ("Demi", 27.0)
BODY_FONT = ("Book", 20.0)
TOAST_OPACITY = 1.0
# Keep the title row compact while retaining the enlarged visible glyph.  The
# previous 128 px slot made the title row consume most of the card height.
ICON_SIZE = 68.0
ICON_RENDER_SCALE = 1.90
MIN_CARD_WIDTH = 560.0
# Restore the previous validated thickness before the last reduction.
DIVIDER_TOTAL_HEIGHT = 4.0
# The native 9-slice's center pixels are authored at alpha 0.5.  Five
# identical passes restore a saturated blue while leaving the opaque orange
# end caps and the original geometry unchanged.
DIVIDER_DOUBLE_PASS = True
DIVIDER_PASS_COUNT = 2
# UMG rounds sub-pixel heights; this produces a visibly thinner intermediate
# line without collapsing the 2 px source texture as a direct 1.5 px request
# did in the live widget.
DIVIDER_RENDER_SCALE_Y = 0.85
# The icon's title-row slot is intentionally taller than the glyph.  Pull the
# divider up into that unused lower part of the row instead of shrinking the
# icon or changing its visible scale.
DIVIDER_TITLE_GAP = -2.0
MAX_PENDING_NOTIFICATIONS = 8
# A few small falling passes are deliberately kept inside the card bounds.
# They are a visual accent only; the toast's normal title/body remains fully
# independent of this optional layer.
GEM_SPRITE_SIZE = 82.0
GEM_TINT = (1.0, 0.82, 0.30, 0.58)
GEM_ANIMATION_DISTANCE = 126.0
GEM_ANIMATION_SPEED = 0.62
GEM_LAYOUT = (
    (18.0, -32.0, 0.82),
    (58.0, 20.0, 0.64),
    (102.0, -4.0, 0.72),
)


def path_of(obj) -> str:
    if obj is None:
        return "<none>"
    try:
        return obj._path_name()
    except Exception:
        return repr(obj)


def make_slate_vector2d(x: float, y: float):
    """Build the legacy SlateBrush ImageSize struct used by BL4's SDK."""
    for struct_name in (
        "DeprecateSlateVector2D",
        "SlateVector2D",
        "Vector2D",
    ):
        try:
            return unrealsdk.make_struct(struct_name, X=float(x), Y=float(y))
        except Exception:
            continue
    raise RuntimeError("no compatible Slate vector struct available")


def enum_member(enum_name: str, member_name: str):
    try:
        enum = unrealsdk.find_enum(enum_name)
        return getattr(enum, member_name, None)
    except Exception:
        return None


def make_slate_color(color):
    """Build a specified SlateColor for a textured SlateBrush.

    In this BL4 SDK a newly-created SlateBrush starts with a zero-alpha
    TintColor.  Border.SetBrushColor is not consistently propagated after a
    Texture2D brush is installed, so the tint must be embedded in the brush.
    """
    linear = unrealsdk.make_struct(
        "LinearColor",
        R=float(color[0]),
        G=float(color[1]),
        B=float(color[2]),
        A=float(color[3]),
    )
    slate = unrealsdk.make_struct("SlateColor")
    slate.SpecifiedColor = linear
    for enum_name in ("ESlateColorStylingMode", "SlateColorStylingMode"):
        specified = enum_member(enum_name, "UseColor_Specified")
        if specified is not None:
            slate.ColorUseRule = specified
            break
    return slate


def apply_divider_texture(log, widget) -> bool:
    """Apply the game's single continuous tooltip/dialog 9-slice separator."""
    texture = None
    texture_path = None
    for candidate_path in DIVIDER_TEXTURE_PATHS:
        try:
            texture = unrealsdk.find_object("Texture2D", candidate_path)
        except Exception as exc:
            log(f"DIVIDER TEXTURE LOOKUP ERROR path={candidate_path} error={exc!r}")
            continue
        if texture is not None:
            texture_path = candidate_path
            break
    if texture is None:
        log("DIVIDER TEXTURE unavailable; using UMG fallback")
        return False

    try:
        brush_fields = {
            "ResourceObject": texture,
            # Preserve the native 36x2 aspect/texel geometry.  The widget
            # height controls the final visual thickness; the source itself
            # must not be replaced by a multi-segment celebratory strip.
            "ImageSize": make_slate_vector2d(36.0, 2.0),
            "Margin": unrealsdk.make_struct(
                "Margin", Left=0.49, Top=0.49, Right=0.49, Bottom=0.49
            ),
        }
        brush = unrealsdk.make_struct("SlateBrush", **brush_fields)
        draw_as = enum_member("ESlateBrushDrawType", "Box")
        if draw_as is not None:
            brush.DrawAs = draw_as
        # Keep the cooked blue/orange pixels unchanged while making the brush
        # visible; a default SlateBrush TintColor is alpha-zero in BL4.
        brush.TintColor = make_slate_color((1.0, 1.0, 1.0, 1.0))
        setter = getattr(widget, "SetBrush", None)
        if setter is None:
            return False
        result = setter(brush)
        # Some BL4 Border subclasses retain their previous BrushColor after a
        # textured brush is installed.  Re-apply neutral white after SetBrush
        # so the asset's native orange/blue colors are not washed out.
        neutral = unrealsdk.make_struct(
            "LinearColor", R=1.0, G=1.0, B=1.0, A=1.0
        )
        optional_call(log, widget, "SetBrushColor", neutral)
        log(
            "DIVIDER TEXTURE BOX "
            f"path={texture_path} result={result!r} tint=neutral-white"
        )
        return True
    except Exception as exc:
        log(f"DIVIDER TEXTURE BOX ERROR path={texture_path} error={exc!r}")
        return False


def fill_horizontal_slot(log, slot):
    """Give a HorizontalBox text slot the remaining row width.

    HAlign_Fill only aligns inside the slot; an automatic-size slot has no
    spare width, so right justification appears to do nothing.  The native
    SlateChildSize Fill rule makes the title occupy the area to the right of
    the icon, allowing the TextBlock's Right justification to be visible.
    """
    size_rule = None
    for enum_name in ("ESlateSizeRule", "SlateSizeRule"):
        size_rule = enum_member(enum_name, "Fill")
        if size_rule is not None:
            break
    if size_rule is None:
        log("TITLE SLOT FILL skip reason=ESlateSizeRule.Fill unavailable")
        return False
    try:
        child_size = unrealsdk.make_struct(
            "SlateChildSize", SizeRule=size_rule, Value=1.0
        )
        setter = getattr(slot, "SetSize", None)
        if setter is None:
            log("TITLE SLOT FILL skip reason=SetSize unavailable")
            return False
        result = setter(child_size)
        log(f"TITLE SLOT FILL result={result!r}")
        return True
    except Exception as exc:
        log(f"TITLE SLOT FILL ERROR {exc!r}")
        return False


def optional_call(log, widget, name: str, *args):
    method = getattr(widget, name, None)
    if method is None:
        log(f"STYLE skip method={name} reason=not exposed")
        return None
    try:
        result = method(*args)
        log(f"STYLE method={name} result={result!r}")
        return result
    except Exception as exc:
        log(f"STYLE method={name} ERROR {exc!r}")
        return None


def silent_call(widget, name: str, *args):
    """Call an animation setter without doing file I/O on the game tick."""
    method = getattr(widget, name, None)
    if method is None:
        return None
    try:
        return method(*args)
    except Exception:
        return None


def weak_pointer(widget):
    """Keep a UObject weakly so map/HUD teardown cannot leave a stale pointer."""
    try:
        return unrealsdk.unreal.WeakPointer(widget)
    except Exception:
        return None


def weak_value(pointer):
    if pointer is None:
        return None
    try:
        return pointer()
    except Exception:
        return None


def live_widget_tree():
    try:
        fallback = None
        for obj in unrealsdk.find_all("WidgetTree", exact=False):
            object_path = path_of(obj).lower()
            if "wbp_primary_layout" not in object_path:
                continue
            if fallback is None:
                fallback = obj
            if "/engine/transient" in object_path or "wbp_primary_layout_c_" in object_path:
                return obj
        return fallback
    except Exception:
        return None


def live_overlay(log):
    try:
        fallback = None
        for obj in unrealsdk.find_all("GbxUIUMGOverlay", exact=False):
            object_path = path_of(obj).lower()
            if "wbp_primary_layout" not in object_path:
                continue
            if fallback is None:
                fallback = obj
            if "/engine/transient" in object_path or "wbp_primary_layout_c_" in object_path:
                log(f"PRIMARY_LAYOUT_OVERLAY overlay={path_of(obj)}")
                return obj
        if fallback is not None:
            log(f"PRIMARY_LAYOUT_OVERLAY fallback={path_of(fallback)}")
            return fallback

        # Keep the exact fallback used by the known-working script.
        points = [
            obj for obj in unrealsdk.find_all("GbxUIUMGExtensionPointWidget", exact=False)
            if path_of(obj).lower().endswith(".bottomright")
        ]
        for point in points:
            try:
                parent = point.GetParent()
                if parent is not None and getattr(parent, "AddChildToOverlay", None) is not None:
                    log(f"BOTTOM_RIGHT_EXTENSION_FALLBACK point={path_of(point)} parent={path_of(parent)}")
                    return parent
            except Exception as exc:
                log(f"BOTTOM_RIGHT_EXTENSION_ERROR point={path_of(point)} error={exc!r}")
    except Exception as exc:
        log(f"OVERLAY SCAN ERROR {exc!r}")
    return None


def construct_widget(log, widget_class, tree, name):
    constructor = getattr(unrealsdk, "construct_object", None)
    if constructor is None:
        raise RuntimeError("unrealsdk.construct_object is not exposed by this SDK build")
    errors = []
    for arguments in ((widget_class, tree, name), (widget_class, tree), (widget_class,)):
        try:
            widget = constructor(*arguments)
            if widget is not None:
                log(f"CONSTRUCT success args={len(arguments)} widget={path_of(widget)}")
                return widget
        except Exception as exc:
            errors.append(repr(exc))
    raise RuntimeError("construct_object failed: " + " | ".join(errors))


def apply_text_color(log, widget, color):
    try:
        linear = unrealsdk.make_struct(
            "LinearColor",
            R=color[0],
            G=color[1],
            B=color[2],
            A=color[3],
        )
        slate = unrealsdk.make_struct("SlateColor")
        try:
            slate.SpecifiedColor = linear
        except Exception as exc:
            log(f"COLOR SpecifiedColor assignment ERROR {exc!r}")
        for enum_name in ("ESlateColorStylingMode", "SlateColorStylingMode"):
            specified = enum_member(enum_name, "UseColor_Specified")
            if specified is not None:
                try:
                    slate.ColorUseRule = specified
                    break
                except Exception as exc:
                    log(f"COLOR ColorUseRule assignment ERROR {exc!r}")
        optional_call(log, widget, "SetColorAndOpacity", slate)
    except Exception as exc:
        log(f"COLOR setup ERROR {exc!r}")


def apply_text_font(log, widget, typeface: str, size: float):
    """Apply the live BL4 Industry font without making font setup hot-path work."""
    try:
        font_object = unrealsdk.find_object("Font", FONT_OBJECT_PATH)
        if font_object is None:
            log(f"FONT object not found path={FONT_OBJECT_PATH}")
            return
        font = unrealsdk.make_struct(
            "SlateFontInfo",
            FontObject=font_object,
            TypefaceFontName=typeface,
            Size=float(size),
            LetterSpacing=0,
            SkewAmount=0.15,
        )
        optional_call(log, widget, "SetFont", font)
    except Exception as exc:
        log(f"FONT setup ERROR typeface={typeface!r} size={size} error={exc!r}")


def apply_text_style(log, widget, color, typeface: str, size: float, justification: str):
    apply_text_color(log, widget, color)
    apply_text_font(log, widget, typeface, size)
    optional_call(log, widget, "SetTextOutlineSize", 0)
    optional_call(
        log,
        widget,
        "SetJustification",
        enum_member("ETextJustify", justification),
    )


def apply_corner_texture(log, widget, tint=(1.0, 1.0, 1.0, 1.0)) -> bool:
    """Try the extracted vanilla online-slideout brush, then fall back cleanly."""
    texture = None
    texture_path = None
    for candidate_path in CORNER_TEXTURE_PATHS:
        try:
            texture = unrealsdk.find_object("Texture2D", candidate_path)
        except Exception as exc:
            log(f"FRAME TEXTURE LOOKUP ERROR path={candidate_path} error={exc!r}")
            continue
        if texture is not None:
            texture_path = candidate_path
            break
    if texture is None:
        log("FRAME TEXTURE unavailable; using simulated rectangular frame")
        return False

    # These normalized margins mirror the extracted CSS border-image slices:
    # generic slideout = 20% top / 49% right / 30% bottom / 49% left; the
    # online slideout uses 49% on all four sides. This keeps the lower-left
    # notch fixed while the center stretches with the card width.
    try:
        if "generic_slideout_background" in str(texture_path):
            brush_margin = unrealsdk.make_struct(
                "Margin", Left=0.49, Top=0.20, Right=0.49, Bottom=0.30
            )
        else:
            brush_margin = unrealsdk.make_struct(
                "Margin", Left=0.49, Top=0.49, Right=0.49, Bottom=0.49
            )
        brush_fields = {
            "ResourceObject": texture,
            "ImageSize": make_slate_vector2d(176.0, 116.0),
            "Margin": brush_margin,
        }
        draw_as = enum_member("ESlateBrushDrawType", "Box")
        if draw_as is not None:
            brush_fields["DrawAs"] = draw_as
        brush = unrealsdk.make_struct("SlateBrush", **brush_fields)
        # The default SlateBrush TintColor is transparent in this runtime.
        # Set it on the brush before handing it to UBorder; SetBrushColor is
        # not consistently propagated after a textured brush is installed.
        brush.TintColor = make_slate_color(tint)
        log(
            f"FRAME TEXTURE TINT path={texture_path} "
            f"rgba={float(tint[0]):.2f},{float(tint[1]):.2f},"
            f"{float(tint[2]):.2f},{float(tint[3]):.2f}"
        )
        setter = getattr(widget, "SetBrush", None)
        if setter is not None:
            result = setter(brush)
            log(f"FRAME TEXTURE BOX path={texture_path} result={result!r}")
            return True
    except Exception as exc:
        log(f"FRAME TEXTURE BOX ERROR path={texture_path} error={exc!r}")

    try:
        setter = getattr(widget, "SetBrushFromTexture", None)
        if setter is not None:
            try:
                result = setter(texture, False)
            except TypeError:
                result = setter(texture)
            log(f"FRAME TEXTURE IMAGE path={texture_path} result={result!r}")
            return True
    except Exception as exc:
        log(f"FRAME TEXTURE IMAGE ERROR path={texture_path} error={exc!r}")
    return False


def icon_file_candidates() -> tuple[Path, ...]:
    candidates = [ICON_WORKSPACE_PATH]
    try:
        candidates.insert(0, Path(__file__).resolve().with_name(ICON_FILE_NAME))
    except Exception:
        pass
    unique = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def live_world_context(log):
    try:
        for controller in unrealsdk.find_all("PlayerController", exact=False):
            object_path = path_of(controller).lower()
            if "default__" not in object_path:
                return controller
    except Exception as exc:
        log(f"ICON WORLD CONTEXT ERROR {exc!r}")
    return None


def resolve_icon_texture(log):
    """Use the reference Moxxi PNG first, then safe cooked fallbacks."""
    # image copy 2.png uses the supplied red/blue Moxxi logo.  Try it before
    # the cooked True Boss icon; the latter is a different, desaturated mark.
    try:
        library = unrealsdk.find_object(
            "KismetRenderingLibrary",
            "/Script/Engine.Default__KismetRenderingLibrary",
        )
        importer = getattr(library, "ImportFileAsTexture2D", None)
        world_context = live_world_context(log)
        if importer is not None and world_context is not None:
            for candidate in icon_file_candidates():
                try:
                    if not candidate.is_file():
                        continue
                    try:
                        result = importer(world_context, str(candidate))
                    except TypeError:
                        result = importer(str(candidate))
                    texture = result[0] if isinstance(result, tuple) and result else result
                    if texture is not None:
                        log(
                            f"ICON CUSTOM IMPORT path={candidate} "
                            f"texture={path_of(texture)}"
                        )
                        return texture, "custom"
                    log(f"ICON CUSTOM IMPORT EMPTY path={candidate}")
                except Exception as exc:
                    log(f"ICON CUSTOM IMPORT ERROR path={candidate} error={exc!r}")
        else:
            log("ICON CUSTOM IMPORT unavailable; trying vanilla texture")
    except Exception as exc:
        log(f"ICON CUSTOM IMPORT SETUP ERROR {exc!r}")

    # Fallback to a cooked game icon if transient PNG import is unavailable.
    for candidate_path in ICON_TEXTURE_PATHS:
        try:
            texture = unrealsdk.find_object("Texture2D", candidate_path)
        except Exception as exc:
            log(f"ICON VANILLA LOOKUP ERROR path={candidate_path} error={exc!r}")
            continue
        if texture is not None:
            if "ico_weekly_true_boss_replay" in candidate_path:
                icon_kind = "big-encore"
            elif "ico_boss_replay" in candidate_path:
                icon_kind = "boss-replay"
            else:
                icon_kind = "vanilla"
            log(f"ICON VANILLA kind={icon_kind} texture={path_of(texture)}")
            return texture, icon_kind
    log("ICON texture unavailable; rendering text-only toast")
    return None, None


def resolve_gem_visual(log):
    """Resolve the optional Boss Replay gem pass as a texture or material."""
    for candidate_path in GEM_TEXTURE_PATHS:
        try:
            visual = unrealsdk.find_object("Texture2D", candidate_path)
        except Exception as exc:
            log(f"GEM TEXTURE LOOKUP ERROR path={candidate_path} error={exc!r}")
            continue
        if visual is not None:
            log(f"GEM VISUAL kind=texture path={path_of(visual)}")
            return visual, "texture"

    for candidate_path in GEM_MATERIAL_PATHS:
        try:
            visual = unrealsdk.find_object("MaterialInterface", candidate_path)
        except Exception as exc:
            log(f"GEM MATERIAL LOOKUP ERROR path={candidate_path} error={exc!r}")
            continue
        if visual is not None:
            log(f"GEM VISUAL kind=material path={path_of(visual)}")
            return visual, "material"

    log("GEM VISUAL unavailable; card will render without gem animation")
    return None, None


def build_gem_sprite(log, tree, image_class, visual, visual_kind, index):
    """Build one transparent gem sprite; returns None on unsupported UMG APIs."""
    try:
        image = construct_widget(log, image_class, tree, TOKEN + f"_Gem{index}")
        optional_call(
            log,
            image,
            "SetDesiredSizeOverride",
            unrealsdk.make_struct(
                "Vector2D", X=GEM_SPRITE_SIZE, Y=GEM_SPRITE_SIZE
            ),
        )
        if visual_kind == "texture":
            setter = getattr(image, "SetBrushFromTexture", None)
            if setter is None:
                log(f"GEM SPRITE {index} skipped: SetBrushFromTexture unavailable")
                return None
            try:
                result = setter(visual, False)
            except TypeError:
                result = setter(visual)
        else:
            setter = getattr(image, "SetBrushFromMaterial", None)
            if setter is None:
                log(f"GEM SPRITE {index} skipped: SetBrushFromMaterial unavailable")
                return None
            result = setter(visual)
        log(f"GEM SPRITE {index} brush kind={visual_kind} result={result!r}")
        tint = unrealsdk.make_struct(
            "LinearColor",
            R=GEM_TINT[0],
            G=GEM_TINT[1],
            B=GEM_TINT[2],
            A=GEM_TINT[3],
        )
        optional_call(log, image, "SetColorAndOpacity", tint)
        optional_call(log, image, "SetOpacity", GEM_TINT[3])
        optional_call(
            log,
            image,
            "SetRenderScale",
            unrealsdk.make_struct(
                "Vector2D", X=GEM_LAYOUT[index][2], Y=GEM_LAYOUT[index][2]
            ),
        )
        return image
    except Exception as exc:
        log(f"GEM SPRITE {index} ERROR {exc!r}")
        return None


def build_gem_layer(log, tree, content_root, visual, visual_kind):
    """Overlay a few animated gem sprites without changing card layout."""
    overlay_class = None
    for class_path in OVERLAY_CLASS_PATHS:
        try:
            candidate = unrealsdk.find_object("Class", class_path)
            log(f"GEM OVERLAY CLASS path={class_path} value={candidate!r}")
            if candidate is not None:
                overlay_class = candidate
                break
        except Exception as exc:
            log(f"GEM OVERLAY CLASS ERROR path={class_path} error={exc!r}")
    if overlay_class is None:
        log("GEM OVERLAY unavailable; keeping normal card root")
        return content_root, []

    image_class = None
    for class_path in IMAGE_CLASS_PATHS:
        try:
            candidate = unrealsdk.find_object("Class", class_path)
            log(f"GEM IMAGE CLASS path={class_path} value={candidate!r}")
            if candidate is not None:
                image_class = candidate
                break
        except Exception as exc:
            log(f"GEM IMAGE CLASS ERROR path={class_path} error={exc!r}")
    if image_class is None:
        log("GEM image class unavailable; keeping normal card root")
        return content_root, []

    try:
        overlay = construct_widget(log, overlay_class, tree, TOKEN + "_GemOverlay")
        content_slot = overlay.AddChild(content_root)
        optional_call(
            log,
            content_slot,
            "SetHorizontalAlignment",
            enum_member("EHorizontalAlignment", "HAlign_Fill"),
        )
        optional_call(
            log,
            content_slot,
            "SetVerticalAlignment",
            enum_member("EVerticalAlignment", "VAlign_Fill"),
        )
        refs = []
        for index, (right_padding, y_offset, _scale) in enumerate(GEM_LAYOUT):
            image = build_gem_sprite(
                log, tree, image_class, visual, visual_kind, index
            )
            if image is None:
                continue
            slot = overlay.AddChild(image)
            optional_call(
                log,
                slot,
                "SetHorizontalAlignment",
                enum_member("EHorizontalAlignment", "HAlign_Right"),
            )
            optional_call(
                log,
                slot,
                "SetVerticalAlignment",
                enum_member("EVerticalAlignment", "VAlign_Center"),
            )
            optional_call(
                log,
                slot,
                "SetPadding",
                unrealsdk.make_struct(
                    "Margin",
                    Left=0.0,
                    Top=0.0,
                    Right=right_padding,
                    Bottom=0.0,
                ),
            )
            optional_call(
                log,
                image,
                "SetRenderTranslation",
                unrealsdk.make_struct("Vector2D", X=0.0, Y=y_offset),
            )
            refs.append(weak_pointer(image))
        if not refs:
            log("GEM OVERLAY produced no sprites; keeping normal card root")
            return content_root, []
        log(f"GEM OVERLAY READY sprites={len(refs)} kind={visual_kind}")
        return overlay, refs
    except Exception as exc:
        log(f"GEM OVERLAY ERROR {exc!r}; keeping normal card root")
        return content_root, []


def build_icon(log, tree, texture):
    if texture is None:
        return None
    image_class = None
    for class_path in IMAGE_CLASS_PATHS:
        try:
            candidate = unrealsdk.find_object("Class", class_path)
            log(f"ICON CLASS path={class_path} value={candidate!r}")
            if candidate is not None:
                image_class = candidate
                break
        except Exception as exc:
            log(f"ICON CLASS ERROR path={class_path} error={exc!r}")
    if image_class is None:
        return None

    try:
        image = construct_widget(log, image_class, tree, TOKEN + "_Icon")
        optional_call(
            log,
            image,
            "SetDesiredSizeOverride",
            unrealsdk.make_struct("Vector2D", X=ICON_SIZE, Y=ICON_SIZE),
        )
        setter = getattr(image, "SetBrushFromTexture", None)
        if setter is not None:
            # UImage's reflected BL4 signature includes bMatchSize. The old
            # one-argument call raised TypeError and removed the icon before
            # it could be added to the card.
            try:
                result = setter(texture, False)
            except TypeError:
                result = setter(texture)
            log(f"ICON BRUSH texture={path_of(texture)} result={result!r}")
        else:
            brush = unrealsdk.make_struct(
                "SlateBrush",
                ResourceObject=texture,
                ImageSize=make_slate_vector2d(ICON_SIZE, ICON_SIZE),
            )
            optional_call(log, image, "SetBrush", brush)
            log(f"ICON BRUSH STRUCT texture={path_of(texture)}")

        # GbxUIUMGImage exposes its own opacity/tint controls.  Leaving these
        # at the inherited defaults can wash out saturated vanilla icons
        # (notably the red True Boss glyph).
        icon_color = unrealsdk.make_struct(
            "LinearColor", R=1.0, G=1.0, B=1.0, A=1.0
        )
        optional_call(log, image, "SetColorAndOpacity", icon_color)
        optional_call(log, image, "SetBrushTintColor", icon_color)
        optional_call(log, image, "SetOpacity", 1.0)
        log("ICON COLOR/TINT forced white opaque")

        render_scale = unrealsdk.make_struct(
            "Vector2D", X=ICON_RENDER_SCALE, Y=ICON_RENDER_SCALE
        )
        optional_call(log, image, "SetRenderScale", render_scale)
        log(f"ICON RENDER SCALE value={ICON_RENDER_SCALE:.2f}")

        # SetDesiredSizeOverride is not honoured consistently by the live
        # GbxUI image class. A SizeBox gives the slot a hard, visible size.
        for class_path in SIZEBOX_CLASS_PATHS:
            try:
                size_class = unrealsdk.find_object("Class", class_path)
                if size_class is None:
                    continue
                icon_box = construct_widget(log, size_class, tree, TOKEN + "_IconSize")
                optional_call(log, icon_box, "SetWidthOverride", ICON_SIZE)
                optional_call(log, icon_box, "SetHeightOverride", ICON_SIZE)
                icon_slot = icon_box.AddChild(image)
                optional_call(
                    log,
                    icon_slot,
                    "SetHorizontalAlignment",
                    enum_member("EHorizontalAlignment", "HAlign_Center"),
                )
                optional_call(
                    log,
                    icon_slot,
                    "SetVerticalAlignment",
                    enum_member("EVerticalAlignment", "VAlign_Center"),
                )
                log(
                    f"ICON SIZEBOX READY size={ICON_SIZE:.1f} "
                    f"wrapper={path_of(icon_box)}"
                )
                return icon_box
            except Exception as exc:
                log(f"ICON SIZEBOX ERROR path={class_path} error={exc!r}")
        return image
    except Exception as exc:
        log(f"ICON BUILD ERROR error={exc!r}")
        return None


class BigEncoreUmgNotification:
    """One proven UMG card with separately styled title/body text."""

    def __init__(self, log):
        self.log = log
        self.widget_ref = None
        self.widget_path = None
        self.content_ref = None
        self.title_ref = None
        self.body_ref = None
        self.accent_ref = None
        self.text_ref = None
        self.icon_texture = None
        self.icon_kind = None
        self.gem_refs = []
        self.gem_visual_kind = None
        self.tree_ref = None
        self.tree_path = None
        self.overlay_ref = None
        self.overlay_path = None
        self.surface_retry_at = 0.0
        self.attached = False
        self.started = None
        self.due = None
        self.removed = True
        self.animated = False
        self.show_count = 0
        self.pending = deque()

    def _resolve_surfaces(self):
        """Reuse the live HUD surfaces; rescan only after they disappear."""
        tree = weak_value(self.tree_ref)
        overlay = weak_value(self.overlay_ref)
        if tree is not None and overlay is not None:
            return tree, overlay

        now = monotonic()
        if now < self.surface_retry_at:
            return None
        self.surface_retry_at = now + 0.75

        if tree is None and self.tree_path:
            try:
                tree = unrealsdk.find_object("WidgetTree", self.tree_path)
            except Exception:
                tree = None
        if overlay is None and self.overlay_path:
            try:
                overlay = unrealsdk.find_object("GbxUIUMGOverlay", self.overlay_path)
            except Exception:
                overlay = None

        if tree is None:
            tree = live_widget_tree()
        if overlay is None:
            overlay = live_overlay(self.log)
        if tree is None or overlay is None:
            return None

        new_tree_path = path_of(tree)
        new_overlay_path = path_of(overlay)
        if ((self.tree_path and self.tree_path != new_tree_path)
                or (self.overlay_path and self.overlay_path != new_overlay_path)):
            # A streamed HUD was replaced.  The old card must not be attached
            # to the new overlay even if its weak wrapper has not expired yet.
            self.widget_ref = None
            self.content_ref = None
            self.title_ref = None
            self.body_ref = None
            self.accent_ref = None
            self.text_ref = None
            self.gem_refs = []
            self.gem_visual_kind = None
            self.widget_path = None
            self.attached = False
        self.tree_path = new_tree_path
        self.overlay_path = new_overlay_path
        self.tree_ref = weak_pointer(tree)
        self.overlay_ref = weak_pointer(overlay)
        self.log(f"HUD SURFACES tree={self.tree_path} overlay={self.overlay_path}")
        return tree, overlay

    def _build_card(self, tree):
        """Construct the card once; later notifications reuse these widgets."""
        widget_class = None
        for class_path in TEXT_CLASS_PATHS:
            try:
                candidate = unrealsdk.find_object("Class", class_path)
                self.log(f"TEXT CLASS path={class_path} value={candidate!r}")
                if candidate is not None:
                    widget_class = candidate
                    break
            except Exception as exc:
                self.log(f"TEXT CLASS ERROR path={class_path} error={exc!r}")
        if widget_class is None:
            raise RuntimeError("no TextBlock class found")

        title_widget = construct_widget(self.log, widget_class, tree, TOKEN + "_Title")
        body_widget = construct_widget(self.log, widget_class, tree, TOKEN + "_Body")
        accent_widget = None
        try:
            accent_widget = construct_widget(
                self.log, widget_class, tree, TOKEN + "_BodyAccent"
            )
        except Exception as exc:
            self.log(f"BODY ACCENT CONSTRUCT ERROR {exc!r}; using one-color body")
        for label, widget in (("title", title_widget), ("body", body_widget)):
            if getattr(widget, "SetText", None) is None:
                raise RuntimeError(f"{label} widget has no SetText: {path_of(widget)}")
        apply_text_style(
            self.log, title_widget, TITLE_COLOR, TITLE_FONT[0], TITLE_FONT[1], "Right"
        )
        apply_text_style(
            self.log, body_widget, BODY_COLOR, BODY_FONT[0], BODY_FONT[1], "Right"
        )
        if accent_widget is not None:
            apply_text_style(
                self.log,
                accent_widget,
                ACCENT_COLOR,
                "Demi",
                BODY_FONT[1],
                "Right",
            )
            optional_call(
                self.log,
                accent_widget,
                "SetTextOutlineSize",
                ACCENT_OUTLINE_SIZE,
            )

        border_class = None
        for class_path in CARD_CLASS_PATHS:
            try:
                candidate = unrealsdk.find_object("Class", class_path)
                self.log(f"CARD CLASS path={class_path} value={candidate!r}")
                if candidate is None:
                    continue
                border_class = candidate
                break
            except Exception as exc:
                self.log(f"CARD CLASS ERROR path={class_path} error={exc!r}")

        # The game icon belongs on the title row, not beside the complete
        # card.  Building this row before the VerticalBox lets the native title
        # and body keep their existing independent layout.
        icon_texture, icon_kind = resolve_icon_texture(self.log)
        self.icon_texture = icon_texture
        self.icon_kind = icon_kind
        title_root = title_widget
        icon = build_icon(self.log, tree, icon_texture)
        if icon is not None:
            horizontal_class = None
            for class_path in HORIZONTAL_CLASS_PATHS:
                try:
                    candidate = unrealsdk.find_object("Class", class_path)
                    self.log(
                        f"TITLE ROW CLASS path={class_path} value={candidate!r}"
                    )
                    if candidate is not None:
                        horizontal_class = candidate
                        break
                except Exception as exc:
                    self.log(f"TITLE ROW CLASS ERROR path={class_path} error={exc!r}")
            if horizontal_class is not None:
                try:
                    title_row = construct_widget(
                        self.log, horizontal_class, tree, TOKEN + "_TitleRow"
                    )
                    optional_call(
                        self.log,
                        title_row,
                        "SetHorizontalAlignment",
                        enum_member("EHorizontalAlignment", "HAlign_Fill"),
                    )
                    optional_call(
                        self.log,
                        title_row,
                        "SetVerticalAlignment",
                        enum_member("EVerticalAlignment", "VAlign_Center"),
                    )
                    icon_slot = title_row.AddChild(icon)
                    optional_call(
                        self.log,
                        icon_slot,
                        "SetHorizontalAlignment",
                        enum_member("EHorizontalAlignment", "HAlign_Left"),
                    )
                    optional_call(
                        self.log,
                        icon_slot,
                        "SetVerticalAlignment",
                        enum_member("EVerticalAlignment", "VAlign_Center"),
                    )
                    optional_call(
                        self.log,
                        icon_slot,
                        "SetPadding",
                        unrealsdk.make_struct(
                            "Margin", Left=0.0, Top=0.0, Right=6.0, Bottom=0.0
                        ),
                    )
                    title_text_slot = title_row.AddChild(title_widget)
                    fill_horizontal_slot(self.log, title_text_slot)
                    optional_call(
                        self.log,
                        title_text_slot,
                        "SetHorizontalAlignment",
                        enum_member("EHorizontalAlignment", "HAlign_Fill"),
                    )
                    optional_call(
                        self.log,
                        title_text_slot,
                        "SetVerticalAlignment",
                        enum_member("EVerticalAlignment", "VAlign_Center"),
                    )
                    title_root = title_row
                    self.log(
                        f"ICON TITLE ROW READY kind={icon_kind} size={ICON_SIZE:.1f} "
                        f"row={path_of(title_row)}"
                    )
                except Exception as exc:
                    self.log(f"ICON TITLE ROW ERROR error={exc!r}; using text title")

        # A VerticalBox is the smallest native UMG container that lets the
        # title/body keep independent fonts and provides a real divider slot.
        # If it is absent, retain the proven single-TextBlock fallback.
        content = None
        title_slot = None
        body_row = None
        for class_path in VERTICAL_CLASS_PATHS:
            try:
                candidate = unrealsdk.find_object("Class", class_path)
                self.log(f"VERTICAL CLASS path={class_path} value={candidate!r}")
                if candidate is None:
                    continue
                try:
                    candidate_content = construct_widget(
                        self.log, candidate, tree, TOKEN + "_Content"
                    )
                    title_slot = candidate_content.AddChild(title_root)
                    title_padding = unrealsdk.make_struct(
                        "Margin", Left=0.0, Top=0.0, Right=0.0, Bottom=1.0
                    )
                    optional_call(
                        self.log,
                        title_slot,
                        "SetHorizontalAlignment",
                        enum_member("EHorizontalAlignment", "HAlign_Fill"),
                    )
                    optional_call(self.log, title_slot, "SetPadding", title_padding)
                    content = candidate_content
                    break
                except Exception as exc:
                    self.log(f"VERTICAL SETUP ERROR path={class_path} error={exc!r}")
            except Exception as exc:
                self.log(f"VERTICAL CLASS ERROR path={class_path} error={exc!r}")

        if content is not None:
            divider = None
            if border_class is not None:
                try:
                    size_class = None
                    for class_path in SIZEBOX_CLASS_PATHS:
                        candidate = unrealsdk.find_object("Class", class_path)
                        self.log(f"SIZEBOX CLASS path={class_path} value={candidate!r}")
                        if candidate is not None:
                            size_class = candidate
                            break
                    divider_line = construct_widget(
                        self.log, border_class, tree, TOKEN + "_DividerLine"
                    )
                    divider_color = unrealsdk.make_struct(
                        "LinearColor",
                        R=DIVIDER_COLOR[0],
                        G=DIVIDER_COLOR[1],
                        B=DIVIDER_COLOR[2],
                        A=DIVIDER_COLOR[3],
                    )
                    optional_call(self.log, divider_line, "SetBrushColor", divider_color)
                    divider_asset = apply_divider_texture(self.log, divider_line)
                    if size_class is not None:
                        divider = construct_widget(
                            self.log, size_class, tree, TOKEN + "_Divider"
                        )
                        optional_call(
                            self.log,
                            divider,
                            "SetHeightOverride",
                            DIVIDER_TOTAL_HEIGHT,
                        )
                        optional_call(
                            self.log,
                            divider,
                            "SetMinDesiredHeight",
                            DIVIDER_TOTAL_HEIGHT,
                        )
                        optional_call(self.log, divider, "SetMinDesiredWidth", 240.0)
                        horizontal_class = None
                        for class_path in HORIZONTAL_CLASS_PATHS:
                            if divider_asset:
                                break
                            try:
                                candidate = unrealsdk.find_object("Class", class_path)
                                if candidate is not None:
                                    horizontal_class = candidate
                                    break
                            except Exception:
                                continue

                        if divider_asset:
                            self.log(
                                f"DIVIDER VANILLA ASSET READY height={DIVIDER_TOTAL_HEIGHT:.1f}"
                            )

                        if horizontal_class is not None:
                            divider_row = construct_widget(
                                self.log,
                                horizontal_class,
                                tree,
                                TOKEN + "_DividerRow",
                            )
                            optional_call(
                                self.log,
                                divider_row,
                                "SetVerticalAlignment",
                                enum_member("EVerticalAlignment", "VAlign_Center"),
                            )
                            optional_call(
                                self.log,
                                divider_row,
                                "SetRenderScale",
                                unrealsdk.make_struct(
                                    "Vector2D",
                                    X=1.0,
                                    Y=DIVIDER_RENDER_SCALE_Y,
                                ),
                            )
                            self.log(
                                f"DIVIDER RENDER SCALE y={DIVIDER_RENDER_SCALE_Y:.2f}"
                            )

                            def fixed_divider_box(name, color, width):
                                segment = construct_widget(
                                    self.log, border_class, tree, name + "Line"
                                )
                                segment_color = unrealsdk.make_struct(
                                    "LinearColor",
                                    R=color[0],
                                    G=color[1],
                                    B=color[2],
                                    A=color[3],
                                )
                                optional_call(
                                    self.log,
                                    segment,
                                    "SetBrushColor",
                                    segment_color,
                                )
                                segment_box = construct_widget(
                                    self.log, size_class, tree, name
                                )
                                optional_call(
                                    self.log,
                                    segment_box,
                                    "SetWidthOverride",
                                    width,
                                )
                                optional_call(
                                    self.log,
                                    segment_box,
                                    "SetHeightOverride",
                                    DIVIDER_TOTAL_HEIGHT,
                                )
                                segment_box.AddChild(segment)
                                return segment_box

                            # Empty SizeBoxes can collapse in the live UMG
                            # prepass. Use transparent Border children so the
                            # edge gaps remain real layout width.
                            transparent = (0.0, 0.0, 0.0, 0.0)
                            left_gap = fixed_divider_box(
                                TOKEN + "_DividerLeftGap",
                                transparent,
                                DIVIDER_EDGE_GAP,
                            )
                            right_gap = fixed_divider_box(
                                TOKEN + "_DividerRightGap",
                                transparent,
                                DIVIDER_EDGE_GAP,
                            )

                            divider_row.AddChild(left_gap)
                            divider_row.AddChild(
                                fixed_divider_box(
                                    TOKEN + "_DividerAccentLeft",
                                    DIVIDER_ACCENT,
                                    DIVIDER_ACCENT_WIDTH,
                                )
                            )
                            main_line_slot = divider_row.AddChild(divider_line)
                            fill_horizontal_slot(self.log, main_line_slot)
                            divider_row.AddChild(
                                fixed_divider_box(
                                    TOKEN + "_DividerAccentRight",
                                    DIVIDER_ACCENT,
                                    DIVIDER_ACCENT_WIDTH,
                                )
                            )
                            divider_row.AddChild(right_gap)
                            divider.AddChild(divider_row)
                            self.log(
                                f"DIVIDER ACCENTS READY gap={DIVIDER_EDGE_GAP:.1f} "
                                f"accent={DIVIDER_ACCENT_WIDTH:.1f}"
                            )
                        else:
                            if divider_asset and DIVIDER_DOUBLE_PASS:
                                overlay_class = None
                                for class_path in OVERLAY_CLASS_PATHS:
                                    try:
                                        candidate = unrealsdk.find_object(
                                            "Class", class_path
                                        )
                                        if candidate is not None:
                                            overlay_class = candidate
                                            break
                                    except Exception:
                                        continue
                                if overlay_class is not None:
                                    divider_overlay = construct_widget(
                                        self.log,
                                        overlay_class,
                                        tree,
                                        TOKEN + "_DividerOverlay",
                                    )
                                    first_slot = divider_overlay.AddChild(divider_line)
                                    optional_call(
                                        self.log,
                                        first_slot,
                                        "SetHorizontalAlignment",
                                        enum_member(
                                            "EHorizontalAlignment", "HAlign_Fill"
                                        ),
                                    )
                                    optional_call(
                                        self.log,
                                        first_slot,
                                        "SetVerticalAlignment",
                                        enum_member(
                                            "EVerticalAlignment", "VAlign_Fill"
                                        ),
                                    )
                                    second_line = construct_widget(
                                        self.log,
                                        border_class,
                                        tree,
                                        TOKEN + "_DividerPass2",
                                    )
                                    second_asset = apply_divider_texture(
                                        self.log, second_line
                                    )
                                    if second_asset:
                                        second_slot = divider_overlay.AddChild(
                                            second_line
                                        )
                                        optional_call(
                                            self.log,
                                            second_slot,
                                            "SetHorizontalAlignment",
                                            enum_member(
                                                "EHorizontalAlignment", "HAlign_Fill"
                                            ),
                                        )
                                        optional_call(
                                            self.log,
                                            second_slot,
                                            "SetVerticalAlignment",
                                            enum_member(
                                                "EVerticalAlignment", "VAlign_Fill"
                                            ),
                                            )
                                    if second_asset and DIVIDER_PASS_COUNT >= 3:
                                        for pass_number in range(3, DIVIDER_PASS_COUNT + 1):
                                            pass_line = construct_widget(
                                                self.log,
                                                border_class,
                                                tree,
                                                TOKEN + f"_DividerPass{pass_number}",
                                            )
                                            pass_asset = apply_divider_texture(
                                                self.log, pass_line
                                            )
                                            if not pass_asset:
                                                continue
                                            pass_slot = divider_overlay.AddChild(pass_line)
                                            optional_call(
                                                self.log,
                                                pass_slot,
                                                "SetHorizontalAlignment",
                                                enum_member(
                                                    "EHorizontalAlignment",
                                                    "HAlign_Fill",
                                                ),
                                            )
                                            optional_call(
                                                self.log,
                                                pass_slot,
                                                "SetVerticalAlignment",
                                                enum_member(
                                                    "EVerticalAlignment",
                                                    "VAlign_Fill",
                                                ),
                                            )
                                    divider.AddChild(divider_overlay)
                                    self.log(
                                        f"DIVIDER VANILLA PASSES READY count={DIVIDER_PASS_COUNT}"
                                    )
                                else:
                                    divider.AddChild(divider_line)
                            else:
                                divider_line_slot = divider.AddChild(divider_line)
                                optional_call(
                                    self.log,
                                    divider_line_slot,
                                    "SetHorizontalAlignment",
                                    enum_member("EHorizontalAlignment", "HAlign_Fill"),
                                )
                                optional_call(
                                    self.log,
                                    divider_line_slot,
                                    "SetVerticalAlignment",
                                    enum_member("EVerticalAlignment", "VAlign_Fill"),
                                )
                                self.log(
                                    f"DIVIDER VANILLA SLOT FILL height={DIVIDER_TOTAL_HEIGHT:.1f}"
                                )
                    else:
                        divider = divider_line
                    divider_slot = content.AddChild(divider)
                    divider_padding = unrealsdk.make_struct(
                        "Margin",
                        Left=1.0,
                        Top=DIVIDER_TITLE_GAP,
                        Right=1.0,
                        Bottom=0.0,
                    )
                    optional_call(
                        self.log,
                        divider_slot,
                        "SetHorizontalAlignment",
                        enum_member("EHorizontalAlignment", "HAlign_Fill"),
                    )
                    optional_call(self.log, divider_slot, "SetPadding", divider_padding)
                    self.log(
                        f"DIVIDER READY widget={path_of(divider)} "
                        f"title_gap={DIVIDER_TITLE_GAP:.1f}"
                    )
                except Exception as exc:
                    self.log(f"DIVIDER SETUP ERROR {exc!r}; continuing without line")

            body_root = body_widget
            body_row = None
            if accent_widget is not None:
                try:
                    body_row_class = None
                    for class_path in HORIZONTAL_CLASS_PATHS:
                        candidate = unrealsdk.find_object("Class", class_path)
                        if candidate is not None:
                            body_row_class = candidate
                            break
                    if body_row_class is not None:
                        body_row = construct_widget(
                            self.log, body_row_class, tree, TOKEN + "_BodyRow"
                        )
                        accent_slot = body_row.AddChild(accent_widget)
                        suffix_slot = body_row.AddChild(body_widget)
                        optional_call(
                            self.log,
                            accent_slot,
                            "SetVerticalAlignment",
                            enum_member("EVerticalAlignment", "VAlign_Center"),
                        )
                        optional_call(
                            self.log,
                            suffix_slot,
                            "SetVerticalAlignment",
                            enum_member("EVerticalAlignment", "VAlign_Center"),
                        )
                        body_root = body_row
                        self.log(
                            "BODY ACCENT ROW READY accent=orange/demi+outline "
                            f"row={path_of(body_row)}"
                        )
                except Exception as exc:
                    self.log(f"BODY ACCENT ROW ERROR {exc!r}; using one-color body")
                    body_row = None

            body_slot = content.AddChild(body_root)
            body_padding = unrealsdk.make_struct(
                "Margin", Left=0.0, Top=2.0, Right=0.0, Bottom=0.0
            )
            optional_call(
                self.log,
                body_slot,
                "SetHorizontalAlignment",
                enum_member(
                    "EHorizontalAlignment",
                    "HAlign_Right" if body_row is not None else "HAlign_Fill",
                ),
            )
            optional_call(self.log, body_slot, "SetPadding", body_padding)
            self.log(
                f"VERTICAL CONTENT READY content={path_of(content)} "
                f"title_slot={title_slot!r} body_slot={body_slot!r}"
            )

        root = content or title_root
        if border_class is not None:
            try:
                surface = construct_widget(
                    self.log, border_class, tree, TOKEN + "_Surface"
                )
                frame = construct_widget(self.log, border_class, tree, TOKEN)
                bg = unrealsdk.make_struct(
                    "LinearColor",
                    R=CARD_BACKGROUND[0],
                    G=CARD_BACKGROUND[1],
                    B=CARD_BACKGROUND[2],
                    A=CARD_BACKGROUND[3],
                )
                optional_call(self.log, surface, "SetBrushColor", bg)
                card_padding = unrealsdk.make_struct(
                    "Margin", Left=24.0, Top=2.0, Right=24.0, Bottom=22.0
                )
                optional_call(self.log, surface, "SetPadding", card_padding)
                optional_call(
                    self.log,
                    surface,
                    "SetHorizontalAlignment",
                    enum_member("EHorizontalAlignment", "HAlign_Fill"),
                )
                optional_call(
                    self.log,
                    surface,
                    "SetVerticalAlignment",
                    enum_member("EVerticalAlignment", "VAlign_Fill"),
                )
                surface_texture = apply_corner_texture(
                    self.log, surface, CARD_TEXTURE_TINT
                )
                if surface_texture:
                    # Preserve the vanilla gradient while lowering its alpha;
                    # the solid colour above remains the fallback when the
                    # cooked asset is not available in this runtime.
                    texture_tint = unrealsdk.make_struct(
                        "LinearColor",
                        R=CARD_TEXTURE_TINT[0],
                        G=CARD_TEXTURE_TINT[1],
                        B=CARD_TEXTURE_TINT[2],
                        A=CARD_TEXTURE_TINT[3],
                    )
                    optional_call(self.log, surface, "SetBrushColor", texture_tint)
                surface_result = surface.AddChild(root)
                self.log(
                    f"CARD ADD CONTENT result={surface_result!r} "
                    f"surface={path_of(surface)}"
                )
                layout_root = surface
                # Border has no portable minimum-width setter in the reflected
                # SDK. Wrap it in a native SizeBox so short messages still
                # produce the broad slideout proportions of the vanilla toast.
                surface_size_class = None
                for class_path in SIZEBOX_CLASS_PATHS:
                    try:
                        candidate = unrealsdk.find_object("Class", class_path)
                        self.log(
                            f"SURFACE SIZEBOX CLASS path={class_path} "
                            f"value={candidate!r}"
                        )
                        if candidate is not None:
                            surface_size_class = candidate
                            break
                    except Exception as exc:
                        self.log(
                            f"SURFACE SIZEBOX CLASS ERROR path={class_path} "
                            f"error={exc!r}"
                        )
                if surface_size_class is not None:
                    try:
                        surface_box = construct_widget(
                            self.log, surface_size_class, tree, TOKEN + "_SurfaceWidth"
                        )
                        optional_call(
                            self.log,
                            surface_box,
                            "SetMinDesiredWidth",
                            MIN_CARD_WIDTH,
                        )
                        surface_box_slot = surface_box.AddChild(surface)
                        optional_call(
                            self.log,
                            surface_box_slot,
                            "SetHorizontalAlignment",
                            enum_member("EHorizontalAlignment", "HAlign_Fill"),
                        )
                        optional_call(
                            self.log,
                            surface_box_slot,
                            "SetVerticalAlignment",
                            enum_member("EVerticalAlignment", "VAlign_Fill"),
                        )
                        layout_root = surface_box
                        self.log(
                            f"CARD MIN WIDTH READY width={MIN_CARD_WIDTH:.1f} "
                            f"wrapper={path_of(surface_box)}"
                        )
                    except Exception as exc:
                        self.log(
                            f"CARD MIN WIDTH ERROR error={exc!r}; using natural width"
                        )
                frame_texture = apply_corner_texture(self.log, frame, CARD_FRAME)
                if not frame_texture:
                    frame_color = unrealsdk.make_struct(
                        "LinearColor",
                        R=CARD_FRAME[0],
                        G=CARD_FRAME[1],
                        B=CARD_FRAME[2],
                        A=CARD_FRAME[3],
                    )
                    optional_call(self.log, frame, "SetBrushColor", frame_color)
                frame_padding = unrealsdk.make_struct(
                    "Margin", Left=1.0, Top=1.0, Right=1.0, Bottom=1.0
                )
                optional_call(self.log, frame, "SetPadding", frame_padding)
                optional_call(
                    self.log,
                    frame,
                    "SetHorizontalAlignment",
                    enum_member("EHorizontalAlignment", "HAlign_Center"),
                )
                optional_call(
                    self.log,
                    frame,
                    "SetVerticalAlignment",
                    enum_member("EVerticalAlignment", "VAlign_Center"),
                )
                frame_result = frame.AddChild(layout_root)
                self.log(
                    f"CARD ADD SURFACE result={frame_result!r} frame={path_of(frame)}"
                )
                root = frame
            except Exception as exc:
                self.log(f"CARD FRAME SETUP ERROR {exc!r}; using unframed root")

        gem_visual, gem_visual_kind = resolve_gem_visual(self.log)
        gem_refs = []
        if gem_visual is not None:
            root, gem_refs = build_gem_layer(
                self.log, tree, root, gem_visual, gem_visual_kind
            )
        self.gem_visual_kind = gem_visual_kind if gem_refs else None
        self.gem_refs = gem_refs
        if gem_refs:
            self.log(
                f"GEM ANIMATION ENABLED sprites={len(gem_refs)} "
                f"kind={self.gem_visual_kind}"
            )

        self.widget_ref = weak_pointer(root)
        self.content_ref = weak_pointer(content)
        self.title_ref = weak_pointer(title_widget)
        self.body_ref = weak_pointer(body_widget) if content is not None else None
        self.accent_ref = (
            weak_pointer(accent_widget)
            if content is not None and body_row is not None
            else None
        )
        # text_ref is retained as a compatibility alias for older cleanup and
        # diagnostics; new code updates title/body independently.
        self.text_ref = self.body_ref or self.title_ref
        if self.widget_ref is None or self.title_ref is None:
            try:
                root.RemoveFromParent()
            except Exception:
                pass
            self.widget_ref = None
            self.content_ref = None
            self.title_ref = None
            self.body_ref = None
            self.accent_ref = None
            self.text_ref = None
            self.gem_refs = []
            self.gem_visual_kind = None
            raise RuntimeError("unrealsdk.unreal.WeakPointer is unavailable")
        self.widget_path = path_of(root)
        optional_call(
            self.log,
            root,
            "SetRenderTransformPivot",
            unrealsdk.make_struct("Vector2D", X=0.5, Y=0.5),
        )
        optional_call(
            self.log,
            root,
            "SetRenderTransformAngle",
            TOAST_ROTATION_DEGREES,
        )
        self.log(f"TOAST ROTATION degrees={TOAST_ROTATION_DEGREES:.2f}")
        self.attached = False
        return root, title_widget, body_widget if content is not None else None

    def _attach_card(self, root, overlay):
        """Attach once and retain the slot; later shows only toggle visibility."""
        add_to_overlay = getattr(overlay, "AddChildToOverlay", None)
        if add_to_overlay is not None:
            try:
                add_result = add_to_overlay(root)
                self.log(f"ADD CHILD TO OVERLAY result={add_result!r} overlay={path_of(overlay)}")
            except Exception as exc:
                self.log(f"ADD CHILD TO OVERLAY ERROR {exc!r}; falling back to AddChild")
                add_result = overlay.AddChild(root)
                self.log(f"ADD CHILD FALLBACK result={add_result!r} overlay={path_of(overlay)}")
        else:
            add_result = overlay.AddChild(root)
            self.log(f"ADD CHILD result={add_result!r} overlay={path_of(overlay)}")

        if add_result is not None:
            optional_call(
                self.log,
                add_result,
                "SetHorizontalAlignment",
                enum_member("EHorizontalAlignment", "HAlign_Right"),
            )
            optional_call(
                self.log,
                add_result,
                "SetVerticalAlignment",
                enum_member("EVerticalAlignment", TOAST_VERTICAL_ALIGNMENT),
            )
            padding = unrealsdk.make_struct(
                "Margin", Left=48.0, Top=0.0, Right=96.0, Bottom=0.0
            )
            optional_call(self.log, add_result, "SetPadding", padding)
            self.log(
                f"TOAST SLOT vertical={TOAST_VERTICAL_ALIGNMENT} "
                "padding=left48/right96/top0/bottom0"
            )
        self.attached = True

    def cleanup(self, reason="cleanup"):
        widget = weak_value(self.widget_ref)
        if widget is not None:
            if reason == "mod disabled":
                try:
                    result = widget.RemoveFromParent()
                    self.log(f"REMOVE reason={reason} result={result!r} widget={self.widget_path or path_of(widget)}")
                except Exception as exc:
                    self.log(f"REMOVE ERROR reason={reason} error={exc!r}")
                self.attached = False
            else:
                collapsed = enum_member("ESlateVisibility", "Collapsed")
                if collapsed is not None:
                    silent_call(widget, "SetVisibility", collapsed)
                silent_call(widget, "SetRenderOpacity", 0.0)
                if reason != "replace" or not self.removed:
                    self.log(f"HIDE reason={reason} widget={self.widget_path or path_of(widget)}")
        elif self.widget_path is not None:
            self.log(f"REMOVE skipped expired widget reason={reason} widget={self.widget_path}")
        if reason == "mod disabled":
            self.pending.clear()
            self.widget_ref = None
            self.content_ref = None
            self.title_ref = None
            self.body_ref = None
            self.accent_ref = None
            self.text_ref = None
            self.icon_texture = None
            self.icon_kind = None
            self.gem_refs = []
            self.gem_visual_kind = None
            self.widget_path = None
            self.attached = False
        self.started = None
        self.due = None
        self.removed = True
        self.animated = False

    def prewarm(self):
        """Build one hidden card before proximity activation needs it."""
        if weak_value(self.widget_ref) is not None and weak_value(self.title_ref) is not None:
            return
        surfaces = self._resolve_surfaces()
        if surfaces is None:
            return
        tree, _overlay = surfaces
        try:
            root, title_widget, body_widget = self._build_card(tree)
            self._attach_card(root, _overlay)
            collapsed = enum_member("ESlateVisibility", "Collapsed")
            if collapsed is not None:
                silent_call(title_widget, "SetVisibility", collapsed)
                if body_widget is not None:
                    silent_call(body_widget, "SetVisibility", collapsed)
                accent_widget = weak_value(self.accent_ref)
                if accent_widget is not None:
                    silent_call(accent_widget, "SetVisibility", collapsed)
                silent_call(root, "SetVisibility", collapsed)
            silent_call(root, "SetRenderOpacity", 0.0)
            self.log(f"CARD PREWARMED root={self.widget_path}")
        except Exception as exc:
            self.log(f"CARD PREWARM ERROR {exc!r}")
            self.widget_ref = None
            self.content_ref = None
            self.title_ref = None
            self.body_ref = None
            self.accent_ref = None
            self.text_ref = None
            self.gem_refs = []
            self.gem_visual_kind = None

    def show(self, title=TITLE, body=BODY, accent=None):
        # Never replace a visible card in-place.  Replacing its text while the
        # animation is active was the source of stacked/frozen widgets and
        # eventual crashes after repeated proximity events.
        if not self.removed and self.started is not None and self.due is not None:
            if weak_value(self.widget_ref) is not None:
                if len(self.pending) < MAX_PENDING_NOTIFICATIONS:
                    self.pending.append((title, body, accent))
                    self.log(
                        f"UMG QUEUED pending={len(self.pending)} "
                        f"title={title!r} accent={accent!r} body={body!r}"
                    )
                else:
                    self.log(
                        f"UMG QUEUE FULL drop={title!r} "
                        f"limit={MAX_PENDING_NOTIFICATIONS}"
                    )
                return False
            self.cleanup("widget expired")
        surfaces = self._resolve_surfaces()
        if surfaces is None:
            raise RuntimeError("live WBP_Primary_Layout WidgetTree/Overlay not found")
        tree, overlay = surfaces
        root = weak_value(self.widget_ref)
        title_widget = weak_value(self.title_ref)
        body_widget = weak_value(self.body_ref)
        accent_widget = weak_value(self.accent_ref)
        if root is None or title_widget is None:
            self.log(f"TREE {path_of(tree)}")
            self.log(f"OVERLAY {path_of(overlay)}")
            root, title_widget, body_widget = self._build_card(tree)
            accent_widget = weak_value(self.accent_ref)

        if body_widget is not None:
            title_result = title_widget.SetText(title)
            body_result = body_widget.SetText(body)
            accent_result = (
                accent_widget.SetText(accent or "")
                if accent_widget is not None
                else None
            )
        else:
            # Compatibility path for an SDK build without VerticalBox.
            title_result = title_widget.SetText(f"{title}\n{accent or ''}{body}")
            body_result = None
            accent_result = None

        visible_value = enum_member("ESlateVisibility", "Visible")
        if visible_value is not None:
            silent_call(title_widget, "SetVisibility", visible_value)
            if body_widget is not None:
                silent_call(body_widget, "SetVisibility", visible_value)
            if accent_widget is not None:
                silent_call(accent_widget, "SetVisibility", visible_value)
            silent_call(root, "SetVisibility", visible_value)
        silent_call(root, "SetRenderOpacity", TOAST_OPACITY)
        silent_call(root, "SetRenderScale", unrealsdk.make_struct("Vector2D", X=1.05, Y=1.05))
        silent_call(root, "SetRenderTranslation", unrealsdk.make_struct("Vector2D", X=0.0, Y=0.0))

        if not self.attached:
            self._attach_card(root, overlay)
        else:
            self.log("CARD ATTACH REUSE skipped; hidden card remains in overlay")

        # _build_card stores weak references.  Reused cards remain attached to
        # the live overlay and are shown/hidden without rebuilding a slot.
        self.widget_path = path_of(root)
        self.started = monotonic()
        self.due = self.started + LIFETIME
        self.removed = False
        self.show_count += 1
        if self.show_count == 1:
            self.log(
                f"UMG SHOW title={title!r} accent={accent!r} "
                f"body={body!r} root={path_of(root)}"
            )

    def _start_queued(self, title, body, accent=None):
        """Swap queued text in-place without a collapsed/empty frame."""
        widget = weak_value(self.widget_ref)
        title_widget = weak_value(self.title_ref)
        body_widget = weak_value(self.body_ref)
        accent_widget = weak_value(self.accent_ref)
        if widget is None or title_widget is None:
            raise RuntimeError("queued notification widget expired")

        if body_widget is not None:
            title_widget.SetText(title)
            body_widget.SetText(body)
            if accent_widget is not None:
                accent_widget.SetText(accent or "")
        else:
            title_widget.SetText(f"{title}\n{accent or ''}{body}")

        visible_value = enum_member("ESlateVisibility", "Visible")
        if visible_value is not None:
            silent_call(title_widget, "SetVisibility", visible_value)
            if body_widget is not None:
                silent_call(body_widget, "SetVisibility", visible_value)
            if accent_widget is not None:
                silent_call(accent_widget, "SetVisibility", visible_value)
            silent_call(widget, "SetVisibility", visible_value)

        now = monotonic()
        self.started = now
        self.due = now + LIFETIME
        self.removed = False
        self.animated = False
        silent_call(widget, "SetRenderOpacity", 0.0)
        silent_call(
            widget,
            "SetRenderScale",
            unrealsdk.make_struct("Vector2D", X=1.05, Y=1.05),
        )
        silent_call(
            widget,
            "SetRenderTranslation",
            unrealsdk.make_struct("Vector2D", X=SLIDE_DISTANCE, Y=0.0),
        )
        self.show_count += 1
        self.log(
            f"UMG DEQUEUED remaining={len(self.pending)} "
            f"title={title!r} accent={accent!r} body={body!r}"
        )

    def _animate_gems(self, elapsed, card_alpha):
        """Move the optional gem sprites without touching the card layout."""
        if not self.gem_refs:
            return
        for index, reference in enumerate(self.gem_refs):
            gem = weak_value(reference)
            if gem is None:
                continue
            _right_padding, base_y, _scale = GEM_LAYOUT[
                min(index, len(GEM_LAYOUT) - 1)
            ]
            phase = (index * 0.31) % 1.0
            progress = (elapsed * GEM_ANIMATION_SPEED + phase) % 1.0
            drift_y = base_y + (progress - 0.5) * GEM_ANIMATION_DISTANCE
            drift_x = sin(elapsed * 2.1 + index * 1.7) * 7.0
            edge_fade = 0.35 + 0.65 * (1.0 - abs(progress * 2.0 - 1.0))
            silent_call(
                gem,
                "SetRenderTranslation",
                unrealsdk.make_struct(
                    "Vector2D", X=drift_x, Y=drift_y
                ),
            )
            silent_call(
                gem,
                "SetRenderOpacity",
                card_alpha * GEM_TINT[3] * edge_fade,
            )

    def tick(self):
        widget = weak_value(self.widget_ref)
        if self.removed or widget is None or self.started is None:
            if not self.removed and widget is None:
                self.cleanup("widget expired")
            self.prewarm()
            return
        elapsed = monotonic() - self.started
        if elapsed < ANIM_IN:
            progress = max(0.0, min(1.0, elapsed / ANIM_IN))
            alpha = progress
            slide = SLIDE_DISTANCE * (1.0 - progress)
        elif elapsed < ANIM_IN + ANIM_HOLD:
            alpha = 1.0
            slide = 0.0
        else:
            progress = max(
                0.0,
                min(1.0, (elapsed - ANIM_IN - ANIM_HOLD) / ANIM_OUT),
            )
            alpha = 1.0 - progress
            slide = SLIDE_DISTANCE * progress
        self._animate_gems(elapsed, alpha)
        # These setters run every HUD tick.  Logging them synchronously to a
        # file caused visible hitching during the notification animation.
        silent_call(widget, "SetRenderOpacity", alpha * TOAST_OPACITY)
        silent_call(
            widget,
            "SetRenderTranslation",
            unrealsdk.make_struct("Vector2D", X=slide, Y=0.0),
        )
        if not self.animated:
            self.log(f"ANIMATION started alpha={alpha:.3f} slide={slide:.1f}")
            self.animated = True
        if self.due is not None and monotonic() >= self.due:
            queued = self.pending.popleft() if self.pending else None
            if queued is not None:
                try:
                    self._start_queued(*queued)
                except Exception as exc:
                    self.log(f"UMG DEQUEUE ERROR error={exc!r}")
                    self.cleanup("queue transition failed")
            else:
                self.cleanup("lifetime elapsed")
