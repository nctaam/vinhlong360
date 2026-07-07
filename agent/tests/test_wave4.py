# agent/tests/test_wave4.py
import inspect

import twofactor


class TestTwoFactorCrypto:
    def test_generate_secret_is_base32(self):
        s = twofactor.generate_secret()
        assert isinstance(s, str) and len(s) >= 16
        # base32 alphabet
        assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in s)

    def test_encrypt_decrypt_roundtrip(self):
        s = twofactor.generate_secret()
        enc = twofactor.encrypt_secret(s)
        assert enc != s  # actually encrypted
        assert twofactor.decrypt_secret(enc) == s

    def test_verify_totp_accepts_current_code(self):
        import pyotp
        s = twofactor.generate_secret()
        code = pyotp.TOTP(s).now()
        assert twofactor.verify_totp(s, code) is True

    def test_verify_totp_rejects_wrong_code(self):
        import pyotp
        s = twofactor.generate_secret()
        real = pyotp.TOTP(s).now()
        # a definitely-wrong 6-digit code is rejected (avoid a 1-in-1e6 collision with `real`)
        wrong = "000000" if real != "000000" else "111111"
        assert twofactor.verify_totp(s, wrong) is False
        # a current code from a DIFFERENT secret must not validate against `s`
        other = pyotp.TOTP(twofactor.generate_secret()).now()
        if other != real:
            assert twofactor.verify_totp(s, other) is False
        # malformed inputs (non-digit / wrong length) are rejected
        assert twofactor.verify_totp(s, "abcdef") is False
        assert twofactor.verify_totp(s, "12345") is False
        assert twofactor.verify_totp(s, "") is False

    def test_provisioning_uri_shape(self):
        uri = twofactor.provisioning_uri("JBSWY3DPEHPK3PXP", "0901234567")
        assert uri.startswith("otpauth://totp/")
        assert "secret=" in uri

    def test_qr_data_uri_is_png(self):
        uri = twofactor.qr_data_uri("otpauth://totp/x?secret=JBSWY3DPEHPK3PXP")
        assert uri.startswith("data:image/png;base64,")

    def test_recovery_codes_generated_and_hashed(self):
        codes = twofactor.generate_recovery_codes(8)
        assert len(codes) == 8
        assert len(set(codes)) == 8  # unique
        h = twofactor.hash_recovery_code(codes[0])
        assert h != codes[0] and len(h) == 64  # sha256 hex


from fastapi import FastAPI
import auth


def _routes():
    app = FastAPI(); app.include_router(auth.router)
    pairs = set()
    for r in app.routes:
        for m in (getattr(r, "methods", None) or set()):
            pairs.add((m, r.path))
    return pairs


class TestTwoFactorEnrollment:
    def test_setup_route_mounted(self):
        assert ("POST", "/auth/2fa/setup") in _routes()

    def test_verify_setup_route_mounted(self):
        assert ("POST", "/auth/2fa/verify-setup") in _routes()

    def test_disable_route_mounted(self):
        assert ("POST", "/auth/2fa/disable") in _routes()

    def test_status_route_mounted(self):
        assert ("GET", "/auth/2fa/status") in _routes()

    def test_setup_stores_encrypted_secret(self):
        src = inspect.getsource(auth.twofa_setup)
        assert "encrypt_secret" in src
        assert "enabled" in src  # inserted disabled

    def test_verify_setup_enables_and_returns_recovery(self):
        src = inspect.getsource(auth.twofa_verify_setup)
        assert "verify_totp" in src
        assert "generate_recovery_codes" in src
        assert "hash_recovery_code" in src

    def test_disable_requires_code(self):
        src = inspect.getsource(auth.twofa_disable)
        assert "verify_totp" in src or "recovery_code_matches" in src

    def test_enrollment_endpoints_require_csrf(self):
        for fn in (auth.twofa_setup, auth.twofa_verify_setup, auth.twofa_disable):
            assert "_require_csrf_lazy" in inspect.getsource(fn)


class TestTwoFactorLoginGate:
    def test_verify_route_mounted(self):
        assert ("POST", "/auth/2fa/verify") in _routes()

    def test_finish_login_helper_exists(self):
        assert callable(auth._finish_login)

    def test_verify_otp_uses_2fa_gate(self):
        src = inspect.getsource(auth.verify_otp)
        assert "_2fa_is_enabled" in src
        assert "two_factor_required" in src

    def test_login_password_uses_2fa_gate(self):
        src = inspect.getsource(auth.login_password)
        assert "_2fa_is_enabled" in src
        assert "two_factor_required" in src

    def test_both_login_paths_use_finish_login(self):
        assert "_finish_login" in inspect.getsource(auth.verify_otp)
        assert "_finish_login" in inspect.getsource(auth.login_password)

    def test_pending_challenge_hashed_and_expiring(self):
        src = inspect.getsource(auth._create_pending_2fa)
        assert "_hash_token" in src
        assert "expires_at" in src

    def test_verify_endpoint_rate_limited_and_attempt_capped(self):
        src = inspect.getsource(auth.twofa_verify)
        assert "_check_shared_auth_rate" in src or "check_rate" in src
        assert "attempts" in src

    def test_verify_supports_recovery_and_remember(self):
        src = inspect.getsource(auth.twofa_verify)
        assert "recovery" in src
        assert "remember_device" in src or "trusted" in src

    def test_pending_2fa_cleanup_registered(self):
        assert "pending_2fa" in inspect.getsource(auth.cleanup_expired_data)

    def test_consume_is_atomic_delete_returning(self):
        # Race-condition fix: the DELETE must be the single atomic consumption
        # point (DELETE ... RETURNING), and its result must gate _finish_login —
        # otherwise two concurrent requests with the same challenge_id + valid
        # code could both pass _load_challenge/_check and each create a session
        # from one single-use challenge.
        src = inspect.getsource(auth.twofa_verify)
        assert "RETURNING" in src
        assert "DELETE FROM pending_2fa" in src
        assert "_finish_login" in src
        # _finish_login must be reachable only after the consume result is checked.
        consume_idx = src.index("_consume")
        finish_idx = src.rindex("_finish_login")
        assert consume_idx < finish_idx


class TestTrustedDevices:
    def test_list_route_mounted(self):
        assert ("GET", "/auth/trusted-devices") in _routes()

    def test_delete_route_mounted(self):
        pairs = _routes()
        assert any(m == "DELETE" and p.startswith("/auth/trusted-devices/") for (m, p) in pairs)

    def test_remember_hashes_token_and_sets_cookie(self):
        src = inspect.getsource(auth._remember_trusted_device)
        assert "_hash_token" in src
        assert "vl360_trusted" in src or "set_cookie" in src

    def test_skip_check_updates_last_used(self):
        src = inspect.getsource(auth._has_valid_trusted_device)
        assert "expires_at" in src
        assert "last_used_at" in src

    def test_login_gate_checks_trusted_device(self):
        assert "_has_valid_trusted_device" in inspect.getsource(auth.verify_otp)
        assert "_has_valid_trusted_device" in inspect.getsource(auth.login_password)

    def test_delete_requires_csrf(self):
        assert "_require_csrf_lazy" in inspect.getsource(auth.delete_trusted_device)

    def test_trusted_cleanup_registered(self):
        assert "trusted_devices" in inspect.getsource(auth.cleanup_expired_data)


class TestSuspiciousLogin:
    def test_helper_exists_and_queries_history(self):
        src = inspect.getsource(auth._check_suspicious_login)
        assert "login_history" in src
        assert "create_notification" in src
        assert "security_alert" in src

    def test_helper_swallows_errors(self):
        src = inspect.getsource(auth._check_suspicious_login)
        assert "except" in src

    def test_no_actor_id_passed(self):
        # security_alert must NOT pass actor_id (no social actor)
        src = inspect.getsource(auth._check_suspicious_login)
        assert "actor_id" not in src

    def test_hooked_in_finish_login(self):
        # single hook site: _finish_login (covers direct logins + post-2FA logins)
        assert "_check_suspicious_login" in inspect.getsource(auth._finish_login)

    def test_not_mapped_in_notif_prefs(self):
        # security_alert must stay unmapped in _NOTIF_TYPE_TO_PREF so it is
        # always delivered (non-suppressible) — see notifications._user_wants_notif.
        import notifications
        assert "security_alert" not in notifications._NOTIF_TYPE_TO_PREF

    def test_check_runs_before_log_login_in_finish_login(self):
        # Ordering guard: _log_login (which INSERTS the current login row) must
        # not have already run by the time _check_suspicious_login's query would
        # see it, otherwise the current row always self-matches and the alert
        # never fires. Concretely: _check_suspicious_login must be scheduled
        # BEFORE the _log_login call in _finish_login's source order.
        src = inspect.getsource(auth._finish_login)
        check_idx = src.index("_check_suspicious_login")
        log_idx = src.index("_log_login")
        assert check_idx < log_idx, (
            "_check_suspicious_login must be launched before _log_login runs, "
            "else the just-inserted current-login row self-matches and the "
            "suspicious-login alert can never fire"
        )


class TestTwoFactorKillSwitch:
    # Wave 4 2FA must ship DARK by default: a global flag gates enrollment and
    # the login challenge so nobody can enable 2FA (and hit the "undecryptable
    # secret if ADMIN_API_KEY rotates" risk) until the owner sets TOTP_ENC_KEY
    # and flips the flag on.

    def test_config_has_two_factor_enabled_flag(self):
        import config
        assert hasattr(config.Settings, "model_fields")
        assert "TWO_FACTOR_ENABLED" in config.Settings.model_fields

    def test_flag_defaults_to_false(self):
        import config
        assert config.settings.TWO_FACTOR_ENABLED is False

    def test_2fa_is_enabled_short_circuits_on_flag(self):
        src = inspect.getsource(auth._2fa_is_enabled)
        assert "TWO_FACTOR_ENABLED" in src
        # the flag check must be the very first statement in the function body,
        # i.e. it appears before the row lookup that follows it.
        flag_idx = src.index("TWO_FACTOR_ENABLED")
        lookup_idx = src.index("_get_2fa_row")
        assert flag_idx < lookup_idx, (
            "TWO_FACTOR_ENABLED must be checked before _get_2fa_row is consulted, "
            "so the flag is a true short-circuit choke point"
        )

    def test_2fa_is_enabled_returns_false_when_flag_off(self, monkeypatch):
        monkeypatch.setattr(auth._cfg, "TWO_FACTOR_ENABLED", False)
        # even if a row would otherwise say enabled, the flag must win first —
        # patch the row lookup to prove the short-circuit never reaches it.
        monkeypatch.setattr(auth, "_get_2fa_row", lambda uid: {"enabled": True})
        assert auth._2fa_is_enabled("any-user-id") is False

    def test_setup_checks_flag_and_403s(self):
        src = inspect.getsource(auth.twofa_setup)
        assert "TWO_FACTOR_ENABLED" in src
        assert "403" in src

    def test_verify_setup_checks_flag_and_403s(self):
        src = inspect.getsource(auth.twofa_verify_setup)
        assert "TWO_FACTOR_ENABLED" in src
        assert "403" in src

    def test_disable_and_status_remain_ungated(self):
        # A user must always be able to turn 2FA off / check status, even
        # while the feature is dark — nobody will have it enabled, but any
        # stray row must remain manageable.
        assert "TWO_FACTOR_ENABLED" not in inspect.getsource(auth.twofa_disable)
        assert "TWO_FACTOR_ENABLED" not in inspect.getsource(auth.twofa_status)

    def test_verify_endpoint_not_separately_gated(self):
        # /2fa/verify is unreachable once the login gate never issues a
        # challenge while the flag is off — no need to double-gate it.
        assert "TWO_FACTOR_ENABLED" not in inspect.getsource(auth.twofa_verify)

    def test_trusted_device_endpoints_not_gated(self):
        assert "TWO_FACTOR_ENABLED" not in inspect.getsource(auth._remember_trusted_device)
        assert "TWO_FACTOR_ENABLED" not in inspect.getsource(auth._has_valid_trusted_device)

    def test_delete_trusted_device_imports_check_rate(self):
        # Regression (SP3 F821): delete_trusted_device gọi check_rate nhưng
        # THIẾU `from ratelimit import check_rate` trong hàm → NameError khi gọi
        # endpoint DELETE /trusted-devices/{id}. Mọi endpoint auth khác import
        # check_rate cục bộ ngay trước khi dùng; hàm này bị sót.
        src = inspect.getsource(auth.delete_trusted_device)
        assert "check_rate(" in src
        assert "from ratelimit import check_rate" in src
