"""Run with: uv run --project integrations/mcp python -m unittest discover -s integrations/mcp."""

import asyncio
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import server
from starlette.responses import JSONResponse


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_week_shopping_preview_uses_summed_planner_grams(self):
        summary = {"shopping": [{"id": "huhn|raw", "name": "Huhn", "state": "raw", "grams": 1000, "recipe_ids": ["a"]}]}
        with patch.object(server, "week_summary", AsyncMock(return_value=summary)):
            preview = await server.preview_week_shopping("week")
        self.assertEqual(preview["items"], [{"name": "Huhn", "state": "raw", "grams": 1000}])

    async def test_week_shopping_write_requires_confirmation(self):
        with patch.object(server, "request", AsyncMock(return_value={})) as request:
            with self.assertRaisesRegex(ValueError, "confirmation"):
                await server.add_week_to_shopping_list("week", "list")
            request.assert_not_awaited()
            await server.add_week_to_shopping_list("week", "list", True)
            request.assert_awaited_once_with("POST", "/api/households/planning/plans/week/shopping-list/list")

    async def test_native_shopping_write_requires_confirmation(self):
        with patch.object(server, "request", AsyncMock(return_value={})) as request:
            with self.assertRaisesRegex(ValueError, "confirmation"):
                await server.add_recipes_to_shopping_list("list", [])
            request.assert_not_awaited()
            payload = [{"recipeId": "r1", "recipeIncrementQuantity": 0.625}]
            await server.add_recipes_to_shopping_list("list", payload, True)
            request.assert_awaited_once_with("POST", "/api/households/shopping/lists/list/recipe", payload)

    async def test_native_check_preserves_fields_and_list_membership(self):
        item = {"id": "one", "note": "Rice", "quantity": 250, "checked": False, "shoppingListId": "list"}
        with (
            patch.object(server, "shopping_list", AsyncMock(return_value={"listItems": [item]})),
            patch.object(server, "request", AsyncMock(return_value={})) as request,
        ):
            await server.check_shopping_item("list", "one", True)
            request.assert_awaited_once_with("PUT", "/api/households/shopping/items", [{**item, "checked": True}])
            with self.assertRaisesRegex(ValueError, "not found"):
                await server.check_shopping_item("list", "foreign", True)

    async def test_credentials_do_not_cross_concurrent_requests(self):
        async def echo(scope, receive, send):
            before = server.USER_TOKEN.get()
            await asyncio.sleep(0)
            assert before == server.USER_TOKEN.get()
            await JSONResponse({"credential": before})(scope, receive, send)

        a, b = "a" * 32, "b" * 32
        with patch.dict(
            os.environ,
            {"MCP_USER_TOKENS": json.dumps({a: "mealie-a", b: "mealie-b"}), "MCP_ALLOWED_HOSTS": "localhost:8080"},
        ):
            app = server.CredentialGateway(echo)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://localhost:8080"
        ) as client:
            responses = await asyncio.gather(
                *[client.get("/mcp", headers={"Authorization": f"Bearer {token}"}) for token in [a, b]]
            )
            self.assertEqual([r.json()["credential"] for r in responses], ["mealie-a", "mealie-b"])
            self.assertEqual((await client.get("/mcp")).status_code, 401)
            self.assertEqual(
                (
                    await client.get("/mcp", headers={"Authorization": f"Bearer {a}", "Host": "evil.invalid"})
                ).status_code,
                403,
            )
            self.assertEqual(
                (
                    await client.get("/mcp", headers={"Authorization": f"Bearer {a}", "Origin": "https://evil.invalid"})
                ).status_code,
                403,
            )
        self.assertEqual(server.USER_TOKEN.get(), "")

    async def test_protocol_initialize_and_tools(self):
        with patch.dict(
            os.environ, {"MCP_USER_TOKENS": json.dumps({"a" * 32: "fixture"}), "MCP_ALLOWED_HOSTS": "localhost:8080"}
        ):
            app = server.CredentialGateway(server.mcp.streamable_http_app())
        async with server.mcp.session_manager.run():
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://localhost:8080",
                headers={"Authorization": "Bearer " + "a" * 32, "Accept": "application/json, text/event-stream"},
            ) as client:
                response = await client.post(
                    "/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-03-26",
                            "capabilities": {},
                            "clientInfo": {"name": "test", "version": "1"},
                        },
                    },
                )
                self.assertEqual(response.status_code, 200)
                self.assertIn("serverInfo", response.json()["result"])
                response = await client.post(
                    "/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
                )
                names = {t["name"] for t in response.json()["result"]["tools"]}
                self.assertTrue(
                    {"preview_week", "confirm_week", "consume_meal", "set_recipe_facts", "my_goal_status"} <= names
                )

    async def test_confirmation_cannot_be_omitted(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            await server.confirm_week({}, 0)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            await server.confirm_my_goals("id", 0)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            await server.delete_recipe("rice")


if __name__ == "__main__":
    unittest.main()
