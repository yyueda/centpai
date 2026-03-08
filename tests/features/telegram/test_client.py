import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.features.telegram.client import TelegramAPI, COMMANDS_TEXT


def make_api(token="test-token"):
    with patch("app.features.telegram.client.httpx.AsyncClient"):
        return TelegramAPI(token=token)


def make_response(ok=True, result=None, description=None, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    data = {"ok": ok}
    if result is not None:
        data["result"] = result
    if description:
        data["description"] = description
    resp.json.return_value = data
    return resp


class TestTelegramAPIInit:
    def test_base_url_contains_token(self):
        api = make_api("mytoken123")
        assert "mytoken123" in api.base

    def test_default_commands_populated(self):
        api = make_api()
        assert len(api.commands) > 0
        command_names = [c["command"] for c in api.commands]
        assert "help" in command_names
        assert "join" in command_names
        assert "leave" in command_names
        assert "expense_add" in command_names
        assert "expense_view" in command_names

    def test_group_is_defaultdict(self):
        api = make_api()
        assert api.group is not None

    def test_expenses_is_defaultdict(self):
        api = make_api()
        assert api.expenses is not None


class TestAclose:
    @pytest.mark.asyncio
    async def test_closes_http_client(self):
        api = make_api()
        api._client.aclose = AsyncMock()
        await api.aclose()
        api._client.aclose.assert_called_once()


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_successful_send(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        result = await api.send_message(chat_id=100, text="Hello")
        api._client.post.assert_called_once()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_includes_chat_id_and_text_in_payload(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        await api.send_message(chat_id=100, text="Hello")
        call_kwargs = api._client.post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["chat_id"] == 100
        assert payload["text"] == "Hello"

    @pytest.mark.asyncio
    async def test_includes_reply_markup_when_provided(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        keyboard = {"inline_keyboard": [[{"text": "OK", "callback_data": "ok"}]]}
        await api.send_message(chat_id=100, text="Hi", reply_markup=keyboard)
        payload = api._client.post.call_args[1]["json"]
        assert "reply_markup" in payload

    @pytest.mark.asyncio
    async def test_includes_parse_mode_when_provided(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        await api.send_message(chat_id=100, text="Hi", parse_mode="Markdown")
        payload = api._client.post.call_args[1]["json"]
        assert payload["parse_mode"] == "Markdown"

    @pytest.mark.asyncio
    async def test_includes_reply_parameters_when_reply_to_set(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        await api.send_message(chat_id=100, text="Hi", reply_to_message_id=42)
        payload = api._client.post.call_args[1]["json"]
        assert payload["reply_parameters"] == {"message_id": 42}

    @pytest.mark.asyncio
    async def test_omits_optional_fields_when_not_provided(self):
        api = make_api()
        resp = make_response(ok=True)
        api._client.post = AsyncMock(return_value=resp)
        await api.send_message(chat_id=100, text="Hi")
        payload = api._client.post.call_args[1]["json"]
        assert "reply_markup" not in payload
        assert "parse_mode" not in payload
        assert "reply_parameters" not in payload

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_ok_false(self):
        api = make_api()
        resp = make_response(ok=False, description="Bad Request")
        api._client.post = AsyncMock(return_value=resp)
        with pytest.raises(RuntimeError, match="send message failed"):
            await api.send_message(chat_id=100, text="Hi")

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self):
        api = make_api()
        api._client.post = AsyncMock(side_effect=Exception("network error"))
        with pytest.raises(Exception):
            await api.send_message(chat_id=100, text="Hi")


class TestSetWebhook:
    @pytest.mark.asyncio
    async def test_successful_set_webhook(self):
        api = make_api()
        resp = make_response(ok=True, result=True)
        api._client.post = AsyncMock(return_value=resp)
        result = await api.set_webhook("https://example.com/hook", "secret123")
        assert result is True

    @pytest.mark.asyncio
    async def test_sends_url_and_secret(self):
        api = make_api()
        resp = make_response(ok=True, result=True)
        api._client.post = AsyncMock(return_value=resp)
        await api.set_webhook("https://example.com/hook", "mysecret")
        payload = api._client.post.call_args[1]["data"]
        assert payload["url"] == "https://example.com/hook"
        assert payload["secret_token"] == "mysecret"

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_ok_false(self):
        api = make_api()
        resp = make_response(ok=False, description="Forbidden")
        api._client.post = AsyncMock(return_value=resp)
        with pytest.raises(RuntimeError, match="set webhook failed"):
            await api.set_webhook("https://example.com", "secret")

    @pytest.mark.asyncio
    async def test_raises_on_exception(self):
        api = make_api()
        api._client.post = AsyncMock(side_effect=Exception("timeout"))
        with pytest.raises(Exception):
            await api.set_webhook("https://example.com", "secret")


class TestGetUpdates:
    @pytest.mark.asyncio
    async def test_returns_json(self):
        api = make_api()
        resp = MagicMock()
        resp.json.return_value = {"ok": True, "result": []}
        api._client.get = AsyncMock(return_value=resp)
        result = await api.get_updates()
        assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_passes_offset(self):
        api = make_api()
        resp = MagicMock()
        resp.json.return_value = {"ok": True, "result": []}
        api._client.get = AsyncMock(return_value=resp)
        await api.get_updates(offset=100)
        params = api._client.get.call_args[1]["params"]
        assert params["offset"] == 100

    @pytest.mark.asyncio
    async def test_offset_none_by_default(self):
        api = make_api()
        resp = MagicMock()
        resp.json.return_value = {"ok": True, "result": []}
        api._client.get = AsyncMock(return_value=resp)
        await api.get_updates()
        params = api._client.get.call_args[1]["params"]
        assert params["offset"] is None


class TestAnswerCallbackQuery:
    @pytest.mark.asyncio
    async def test_posts_callback_query_id(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query(callback_query_id="cq123")
        payload = api._client.post.call_args[1]["json"]
        assert payload["callback_query_id"] == "cq123"

    @pytest.mark.asyncio
    async def test_includes_text_when_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query("cq1", text="Done!")
        payload = api._client.post.call_args[1]["json"]
        assert payload["text"] == "Done!"

    @pytest.mark.asyncio
    async def test_omits_text_when_not_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query("cq1")
        payload = api._client.post.call_args[1]["json"]
        assert "text" not in payload

    @pytest.mark.asyncio
    async def test_includes_show_alert_when_true(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query("cq1", show_alert=True)
        payload = api._client.post.call_args[1]["json"]
        assert payload["show_alert"] is True

    @pytest.mark.asyncio
    async def test_includes_url_when_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query("cq1", url="https://example.com")
        payload = api._client.post.call_args[1]["json"]
        assert payload["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_includes_cache_time_when_nonzero(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.answer_callback_query("cq1", cache_time=30)
        payload = api._client.post.call_args[1]["json"]
        assert payload["cache_time"] == 30


class TestSetMyCommands:
    @pytest.mark.asyncio
    async def test_posts_commands(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        commands = [{"command": "help", "description": "Help"}]
        await api.setMyCommands(commands)
        payload = api._client.post.call_args[1]["json"]
        assert payload["commands"] == commands

    @pytest.mark.asyncio
    async def test_includes_scope_when_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        scope = {"type": "all_group_chats"}
        await api.setMyCommands([], scope=scope)
        payload = api._client.post.call_args[1]["json"]
        assert payload["scope"] == scope

    @pytest.mark.asyncio
    async def test_includes_language_code_when_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.setMyCommands([], language_code="en")
        payload = api._client.post.call_args[1]["json"]
        assert payload["language_code"] == "en"

    @pytest.mark.asyncio
    async def test_omits_optional_fields_when_not_provided(self):
        api = make_api()
        api._client.post = AsyncMock(return_value=MagicMock())
        await api.setMyCommands([])
        payload = api._client.post.call_args[1]["json"]
        assert "scope" not in payload
        assert "language_code" not in payload


class TestCommandsText:
    def test_contains_all_key_commands(self):
        for cmd in ["/help", "/join", "/leave", "/members", "/expense_add",
                    "/expense_view", "/expense_remove", "/pay"]:
            assert cmd in COMMANDS_TEXT

    def test_contains_split_rules_section(self):
        assert "Split Rules" in COMMANDS_TEXT

    def test_contains_example(self):
        assert "Example" in COMMANDS_TEXT