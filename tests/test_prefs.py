import re
import sys

import pytest

from invisible_playwright._fpforge import generate_profile
from invisible_playwright.prefs import (
    _accept_language,
    _font_metrics_for_platform,
    _WIN_LIGHT_COLORS,
    translate_profile_to_prefs,
)


@pytest.mark.unit
def test_translate_includes_gpu_renderer_windows():
    """On Windows, renderer/vendor are cleared so ANGLE reports native hardware."""
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.webgl.renderer"] == ""
    assert prefs["zoom.stealth.webgl.vendor"] == ""


@pytest.mark.unit
def test_translate_includes_screen():
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.screen.width"] == p.screen.width
    assert prefs["zoom.stealth.screen.height"] == p.screen.height


@pytest.mark.unit
def test_translate_is_deterministic_per_seed():
    a = translate_profile_to_prefs(generate_profile(seed=42))
    b = translate_profile_to_prefs(generate_profile(seed=42))
    assert a == b


@pytest.mark.unit
def test_translate_varies_across_seeds():
    a = translate_profile_to_prefs(generate_profile(seed=1))
    b = translate_profile_to_prefs(generate_profile(seed=2))
    assert a != b


@pytest.mark.unit
def test_translate_has_stealth_baseline_constants():
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert prefs.get("privacy.resistFingerprinting") is False
    assert "media.peerconnection.enabled" in prefs


# ──────────────────────────────────────────────────────────────────────
#  _accept_language (platform-agnostic)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_accept_language_with_region():
    # AL1
    assert _accept_language("en-US") == "en-US, en"


@pytest.mark.unit
def test_accept_language_no_region():
    # AL2
    assert _accept_language("fr") == "fr"


@pytest.mark.unit
def test_accept_language_underscore_normalized():
    # AL3
    assert _accept_language("pt_BR") == "pt-BR, pt"


# ──────────────────────────────────────────────────────────────────────
#  _font_metrics_for_platform
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_font_metrics_windows_returns_empty(monkeypatch):
    # FM2: Windows never applies width-scale factors.
    monkeypatch.setattr(sys, "platform", "win32")
    assert _font_metrics_for_platform("Arial|1.0,Verdana|0.9,") == ""


@pytest.mark.unit
def test_font_metrics_empty_input_returns_empty():
    # FM3: Empty input always returns "" regardless of platform.
    assert _font_metrics_for_platform("") == ""


# ──────────────────────────────────────────────────────────────────────
#  Platform-specific GPU / MSAA (Windows)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_gpu_renderer_empty_on_windows(monkeypatch):
    # PG2
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.webgl.renderer"] == ""
    assert prefs["zoom.stealth.webgl.vendor"] == ""


@pytest.mark.unit
def test_msaa_pinned_to_4_on_windows(monkeypatch):
    # PG4: even when profile.webgl.msaa_samples differs, Windows pins to 4.
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42, pin={"webgl.msaa_samples": 8})
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.webgl.msaa"] == 4
    assert prefs["webgl.msaa-samples"] == 4
    assert prefs["webgl.msaa-force"] is True


# ──────────────────────────────────────────────────────────────────────
#  Canvas noise skip mask (Windows always uses intel path)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_canvas_noise_mask_windows_uses_intel_path(monkeypatch):
    # CN3: on Windows _renderer_lo is hardcoded to "intel" → mask=15.
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(
        seed=42,
        pin={"gpu.renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4090 Direct3D11)"},
    )
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.canvas.noise_skip_mask"] == 15


# ──────────────────────────────────────────────────────────────────────
#  WebGL extensions (Windows clears them)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_webgl_extensions_cleared_on_windows(monkeypatch):
    # WE2
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert prefs["zoom.stealth.webgl.extensions"] == ""
    assert prefs["zoom.stealth.webgl2.extensions"] == ""


# ──────────────────────────────────────────────────────────────────────
#  Timezone (platform-agnostic)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_timezone_set_propagates_to_both_keys():
    # TZ1
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, timezone="America/New_York")
    assert prefs["zoom.stealth.timezone"] == "America/New_York"
    assert prefs["juggler.timezone.override"] == "America/New_York"


@pytest.mark.unit
def test_timezone_empty_omits_both_keys():
    # TZ2
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, timezone="")
    assert "zoom.stealth.timezone" not in prefs
    assert "juggler.timezone.override" not in prefs


# ──────────────────────────────────────────────────────────────────────
#  extra_prefs overlay (platform-agnostic)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_extra_prefs_adds_custom_key():
    # EP1
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, extra_prefs={"custom.pref": 42})
    assert prefs["custom.pref"] == 42


@pytest.mark.unit
def test_extra_prefs_none_value_deletes_key():
    # EP2
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(
        p, extra_prefs={"privacy.resistFingerprinting": None}
    )
    assert "privacy.resistFingerprinting" not in prefs


@pytest.mark.unit
def test_extra_prefs_overrides_existing_key():
    # EP3
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, extra_prefs={"zoom.stealth.seed": 999})
    assert prefs["zoom.stealth.seed"] == 999


@pytest.mark.unit
def test_extra_prefs_none_is_no_op():
    # EP4
    p = generate_profile(seed=42)
    base = translate_profile_to_prefs(p)
    with_none = translate_profile_to_prefs(p, extra_prefs=None)
    assert base == with_none


@pytest.mark.unit
def test_extra_prefs_empty_dict_is_no_op():
    # EP5
    p = generate_profile(seed=42)
    base = translate_profile_to_prefs(p)
    with_empty = translate_profile_to_prefs(p, extra_prefs={})
    assert base == with_empty


# ──────────────────────────────────────────────────────────────────────
#  System colors / dark theme (platform-agnostic — palette is Win10)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_system_colors_present_when_light_theme():
    # SC1
    p = generate_profile(seed=42, pin={"dark_theme": False})
    prefs = translate_profile_to_prefs(p)
    assert prefs["ui.systemUsesDarkTheme"] == 0
    # Spot-check a few keys from the Win10 light palette.
    for key in _WIN_LIGHT_COLORS:
        assert key in prefs
        assert prefs[key] == _WIN_LIGHT_COLORS[key]


@pytest.mark.unit
def test_system_colors_absent_when_dark_theme():
    # SC2
    p = generate_profile(seed=42, pin={"dark_theme": True})
    prefs = translate_profile_to_prefs(p)
    assert prefs["ui.systemUsesDarkTheme"] == 1
    for key in _WIN_LIGHT_COLORS:
        assert key not in prefs


# ──────────────────────────────────────────────────────────────────────
#  Locale prefs (platform-agnostic)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_locale_en_us_accept_languages():
    # LC1
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, locale="en-US")
    assert prefs["intl.accept_languages"] == "en-US, en"


@pytest.mark.unit
def test_locale_underscore_form_normalized():
    # LC2
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, locale="de_DE")
    assert prefs["intl.accept_languages"] == "de-DE, de"
    assert prefs["general.useragent.locale"] == "de-DE"
    assert prefs["intl.locale.requested"] == "de-DE"


@pytest.mark.unit
def test_locale_empty_falls_back_to_en_us():
    # LC3
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, locale="")
    assert prefs["intl.accept_languages"] == "en-US, en"


# ──────────────────────────────────────────────────────────────────────
#  Xvfb workarounds (Windows must NOT set Linux-only keys)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_xvfb_workarounds_absent_on_windows(monkeypatch):
    # XW2
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    assert "gfx.webrender.all" not in prefs
    assert "gfx.webrender.force-disabled" not in prefs
    assert "webgl.force-enabled" not in prefs


# ──────────────────────────────────────────────────────────────────────
#  Windows virtual-desktop workarounds
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_virtual_display_workaround_applied_on_windows(monkeypatch):
    # VD1
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, virtual_display=True)
    assert prefs["security.sandbox.gpu.level"] == 0


@pytest.mark.unit
def test_virtual_display_workaround_absent_when_disabled(monkeypatch):
    # VD2
    monkeypatch.setattr(sys, "platform", "win32")
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p, virtual_display=False)
    assert "security.sandbox.gpu.level" not in prefs


# ──────────────────────────────────────────────────────────────────────
#  Seed-derived LAN IP (platform-agnostic)
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_lan_ip_matches_192_168_pattern():
    # LI1
    p = generate_profile(seed=42)
    prefs = translate_profile_to_prefs(p)
    ip = prefs["zoom.stealth.webrtc.host_ip"]
    m = re.match(r"^192\.168\.(\d+)\.(\d+)$", ip)
    assert m, f"unexpected LAN IP format: {ip!r}"
    o3, o4 = int(m.group(1)), int(m.group(2))
    assert 1 <= o3 <= 254
    assert 1 <= o4 <= 254


@pytest.mark.unit
def test_lan_ip_deterministic_per_seed():
    # LI2
    a = translate_profile_to_prefs(generate_profile(seed=42))["zoom.stealth.webrtc.host_ip"]
    b = translate_profile_to_prefs(generate_profile(seed=42))["zoom.stealth.webrtc.host_ip"]
    assert a == b


@pytest.mark.unit
def test_lan_ip_seed_zero_has_no_zero_octets():
    # LI3: code adds +1 so neither dynamic octet should ever be 0.
    p = generate_profile(seed=0)
    prefs = translate_profile_to_prefs(p)
    ip = prefs["zoom.stealth.webrtc.host_ip"]
    octets = ip.split(".")
    assert octets[0] == "192"
    assert octets[1] == "168"
    assert int(octets[2]) >= 1
    assert int(octets[3]) >= 1
