from __future__ import annotations

import logging


def test_bot_gateway_logger_redacts_message_and_token(caplog):
    import agent.bot_gateway as bot_gateway

    with caplog.at_level(logging.INFO, logger="bot_gateway"):
        bot_gateway._bot_logger.info("message=%s token=%s", "0901234567", "secret-token")
    output = " ".join(record.getMessage() for record in caplog.records)
    assert "0901234567" not in output
    assert "secret-token" not in output


def test_bot_app_openapi_exposes_webhook_auth_metadata():
    import agent.bot_gateway as bot_gateway

    app = bot_gateway.create_bot_app()
    routes = {route.path: route for route in app.routes if hasattr(route, "path")}
    assert "/webhook/zalo" in routes
    operation = routes["/webhook/zalo"].openapi_extra or {}
    assert operation.get("x-auth") == "hmac"
