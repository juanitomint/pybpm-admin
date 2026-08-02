"""Integration tests — admin API endpoints with mocked pybpm-api backend."""


class TestGetTree:
    """GET /admin/get_tree/json — nested tree for ExtJS TreePanel."""

    def test_returns_200_with_session_cookie(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/admin/get_tree/json", headers=session_headers)
        assert resp.status_code == 200

    def test_response_has_root_structure(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_tree/json", headers=session_headers
        ).json()
        assert "id" in data
        assert "item" in data

    def test_root_item_is_home(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        items = sync_test_client.get(
            "/admin/get_tree/json", headers=session_headers
        ).json()["item"]
        home = next(i for i in items if i["text"] == "Home")
        assert home["id"] == 1

    def test_tree_contains_model_nodes(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        """Each model from pybpm-api should appear as a leaf node in the tree."""

        def _is_model_node(n):  # type: ignore[no-untyped-def]
            if "userdata" not in n:
                return False
            ud = {u["name"]: u["content"] for u in n["userdata"]}
            return ud.get("ismodel") is True

        def _collect_leaves(nodes):  # type: ignore[no-untyped-def]
            leaves = []
            for n in nodes:
                if _is_model_node(n):
                    leaves.append(n)
                elif "item" in n:
                    leaves.extend(_collect_leaves(n["item"]))
            return leaves

        home_children = sync_test_client.get(
            "/admin/get_tree/json",
            headers=session_headers,
        ).json()["item"][0]["item"]
        all_leaves = _collect_leaves(home_children)
        assert len(all_leaves) >= 3

    def test_leaf_nodes_have_idwf_userdata(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]

        def _is_model_node(n):  # type: ignore[no-untyped-def]
            if "userdata" not in n:
                return False
            ud = {u["name"]: u["content"] for u in n["userdata"]}
            return ud.get("ismodel") is True

        def _find_leaves(nodes):  # type: ignore[no-untyped-def]
            leaves = []
            for n in nodes:
                if _is_model_node(n):
                    leaves.append(n)
                elif "item" in n:
                    leaves.extend(_find_leaves(n["item"]))
            return leaves

        home_children = sync_test_client.get(
            "/admin/get_tree/json",
            headers=session_headers,
        ).json()["item"][0]["item"]
        leaves = _find_leaves(home_children)
        for leaf in leaves:
            ud = {u["name"]: u["content"] for u in leaf["userdata"]}
            assert "idwf" in ud
            assert ud["ismodel"] is True


class TestGetTree2:
    """GET /admin/get_tree2/json — flat tree with leaf/cls fields."""

    def test_returns_200(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/admin/get_tree2/json", headers=session_headers)
        assert resp.status_code == 200

    def test_response_is_list_of_nodes(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_tree2/json", headers=session_headers
        ).json()
        assert isinstance(data, list)

    def test_folder_nodes_have_no_id_and_leaf_false(
        self, sync_test_client, session_headers
    ):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_tree2/json", headers=session_headers
        ).json()
        folders = [n for n in data if not n.get("leaf")]
        assert len(folders) >= 1
        for folder in folders:
            assert "id" not in folder
            assert folder["cls"] == "folder"

    def test_folder_nodes_have_children(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_tree2/json", headers=session_headers
        ).json()
        folders_with_children = [n for n in data if not n["leaf"] and n.get("children")]
        assert len(folders_with_children) >= 1

    def test_leaf_nodes_have_id_and_text(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]

        def _collect_leaves(nodes):  # type: ignore[no-untyped-def]
            leaves = []
            for n in nodes:
                if n.get("leaf"):
                    leaves.append(n)
                elif "children" in n and isinstance(n["children"], list):
                    leaves.extend(_collect_leaves(n["children"]))
            return leaves

        data = sync_test_client.get(
            "/admin/get_tree2/json", headers=session_headers
        ).json()
        all_leaves = _collect_leaves(data)
        assert len(all_leaves) >= 1
        for leaf in all_leaves:
            assert "id" in leaf
            assert "text" in leaf


class TestGetModels:
    """GET /admin/get_models — flat list of all models."""

    def test_returns_200(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/admin/get_models", headers=session_headers)
        assert resp.status_code == 200

    def test_response_is_list(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get("/admin/get_models", headers=session_headers).json()
        assert isinstance(data, list)

    def test_contains_all_mocked_models(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        ids = {
            m["idwf"]
            for m in sync_test_client.get(
                "/admin/get_models",
                headers=session_headers,
            ).json()
        }
        assert "test-01" in ids
        assert "test-loop" in ids
        assert "subproc-02" in ids

    def test_filter_by_folder(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_models?folder=HR",
            headers=session_headers,
        ).json()
        assert len(data) == 1
        assert data[0]["idwf"] == "subproc-02"

    def test_default_ordering_by_name(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        names = [
            m["name"]
            for m in sync_test_client.get(
                "/admin/get_models",
                headers=session_headers,
            ).json()
        ]
        assert names == sorted(names)


class TestGetModel:
    """GET /admin/get_model/{idwf} — single model data."""

    def test_returns_200(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin/get_model/test-01",
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_response_contains_idwf(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_model/test-01",
            headers=session_headers,
        ).json()
        assert data["idwf"] == "test-01"

    def test_response_contains_svg(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/get_model/test-01",
            headers=session_headers,
        ).json()
        assert "svg" in data


class TestTreeCreate:
    """POST /admin/tree/create — create new model scaffold."""

    def test_create_new_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/create",
            json={"idwf": "new-model-01", "folder": "General"},
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_create_requires_idwf(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/create",
            json={"folder": "General"},
            headers=session_headers,
        )
        assert resp.status_code == 400

    def test_create_with_nondefault_folder_succeeds(
        self, sync_test_client, session_headers
    ):  # type: ignore[no-untyped-def]
        """Creating a model in a non-default folder should succeed end-to-end."""
        resp = sync_test_client.post(
            "/admin/tree/create",
            json={"idwf": "folder-test", "folder": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True


class TestTreeDestroy:
    """POST /admin/tree/destroy — delete a model."""

    def test_destroy_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/destroy",
            json={"id": "test-01"},
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_destroy_requires_idwf(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/destroy",
            json={},
            headers=session_headers,
        )
        assert resp.status_code == 400


class TestTreeUpdate:
    """POST /admin/tree/update — move model to folder."""

    def test_update_single_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/update",
            json={"id": "test-01", "parentId": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_update_multiple_models(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/tree/update",
            json=[
                {"id": "test-01", "parentId": "HR"},
                {"id": "test-loop", "parentId": "General"},
            ],
            headers=session_headers,
        )
        assert resp.status_code == 200


class TestModelMove:
    """POST /admin/model_move — move model between folders."""

    def test_move_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/model_move",
            json={"idwf": "test-01", "folder": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_move_requires_idwf_and_folder(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/model_move",
            json={"folder": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 400

    def test_move_accepts_to_key(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        """The legacy endpoint accepted 'to' as alias for folder."""
        resp = sync_test_client.post(
            "/admin/model_move",
            json={"idwf": "test-01", "to": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200


class TestImportForm:
    """GET /admin/import_form — import form config."""

    def test_returns_200(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get("/admin/import_form", headers=session_headers)
        assert resp.status_code == 200

    def test_response_has_upload_config(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        data = sync_test_client.get(
            "/admin/import_form",
            headers=session_headers,
        ).json()
        assert "upload_url" in data
        assert data["accept"] == ".zip"


class TestNewModelForm:
    """GET /admin/new_model_form — available folders list."""

    def test_returns_200(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.get(
            "/admin/new_model_form",
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_response_contains_general_folder(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        folders = {
            f["folder"]
            for f in sync_test_client.get(
                "/admin/new_model_form",
                headers=session_headers,
            ).json()["folders"]
        }
        assert "General" in folders

    def test_folders_are_sorted(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        folders = [
            f["folder"]
            for f in sync_test_client.get(
                "/admin/new_model_form",
                headers=session_headers,
            ).json()["folders"]
        ]
        assert folders == sorted(folders)


class TestExplodeTreeUtility:
    """Test the _explode_tree pure function with various inputs."""

    def test_flat_dict_becomes_nested(self):  # type: ignore[no-untyped-def]
        from admin_router import _explode_tree

        result = _explode_tree({"General/model1": "M1", "HR/onboard": "Onboard"})
        assert "General" in result
        assert "model1" in result["General"]
        assert result["General"]["model1"] == "M1"
        assert "HR" in result

    def test_deeply_nested_paths(self):  # type: ignore[no-untyped-def]
        from admin_router import _explode_tree

        result = _explode_tree({"A/B/C/deep": "Deep"})
        assert result["A"]["B"]["C"]["deep"] == "Deep"

    def test_empty_dict_returns_empty(self):  # type: ignore[no-untyped-def]
        from admin_router import _explode_tree

        result = _explode_tree({})
        assert result == {}

    def test_non_dict_input_returns_false(self):  # type: ignore[no-untyped-def]
        from admin_router import _explode_tree

        assert _explode_tree("not a dict") is False
        assert _explode_tree([]) is False


class TestConvertToItemUtility:
    """Test the _convert_to_item pure function."""

    def test_converts_leaf_nodes(self):  # type: ignore[no-untyped-def]
        from admin_router import _convert_to_item

        nested = {"General": {"test-01": "My Model"}}
        result = _convert_to_item(nested, 1)
        assert len(result) == 1
        general_node = result[0]
        assert general_node["text"] == "General"
        assert general_node["child"] == 1

    def test_leaf_nodes_have_userdata(self):  # type: ignore[no-untyped-def]
        from admin_router import _convert_to_item

        nested = {"test-01": "My Model"}
        result = _convert_to_item(nested, 1)
        leaf = result[0]
        assert "userdata" in leaf
        ud = {u["name"]: u["content"] for u in leaf["userdata"]}
        assert ud["idwf"] == "test-01"


class TestConvertToExtUtility:
    """Test the _convert_to_ext pure function."""

    def test_folder_nodes_not_leaf(self):  # type: ignore[no-untyped-def]
        from admin_router import _convert_to_ext

        nested = {"General": {"model1": "M1"}}
        result = _convert_to_ext(nested)
        folder_node = next(n for n in result if not n["leaf"])
        assert folder_node["cls"] == "folder"
        assert folder_node["leaf"] is False

    def test_leaf_nodes_have_icon_cls(self):  # type: ignore[no-untyped-def]
        from admin_router import _convert_to_ext

        result = _convert_to_ext({"model1": "M1"})
        leaf = next(n for n in result if n["leaf"])
        assert "iconCls" in leaf


class TestBackendTokenForwarding:
    """Verify the bearer token is forwarded to pybpm-api."""

    def test_auth_headers_pass_through_to_backend(
        self, sync_test_client, session_headers
    ):  # type: ignore[no-untyped-def]
        """A valid Bearer token should allow get_models to succeed."""
        resp = sync_test_client.get(
            "/admin/get_models",
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_valid_token_allows_get_tree(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        """With the mock token, get_tree should return a proper nested tree."""
        resp = sync_test_client.get(
            "/admin/get_tree/json",
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        home = next(i for i in data["item"] if i["text"] == "Home")
        assert home["id"] == 1

    def test_valid_token_allows_get_tree2(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        """With the mock token, get_tree2 should return leaf/children format."""
        resp = sync_test_client.get(
            "/admin/get_tree2/json",
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestRepositoryAddProxy:
    """POST /admin/repository/add/{idwf} — proxy to pybpm-api POST /add/{idwf}.

    Used by tree.js ModelAdd action from the browser UI.
    """

    def test_add_creates_scaffold_via_backend(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/repository/add/test-new",
            data={"folder": "General"},
            headers=session_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True

    def test_add_with_folder_moves_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        """Creating in a non-default folder should also call update_folder."""
        import admin_router as ar

        calls = []
        original_call_backend = ar._call_backend

        async def track_calls(*args, **kwargs):  # type: ignore[no-untyped-def]
            calls.append((args[1], args[2]))
            return await original_call_backend(*args, **kwargs)

        from unittest import mock

        with mock.patch.object(ar, "_call_backend", side_effect=track_calls):
            resp = sync_test_client.post(
                "/admin/repository/add/test-newfolder",
                data={"folder": "HR"},
                headers=session_headers,
            )
            assert resp.status_code == 200

        methods_paths = [(m, p) for m, p in calls]
        add_call = [c for c in methods_paths if c[1].startswith("/add/")]
        folder_call = [c for c in methods_paths if c[1] == "/update_folder"]
        assert len(add_call) == 1
        assert len(folder_call) == 1


class TestRepositoryDuplicateProxy:
    """POST /admin/repository/duplicate — proxy to pybpm-api POST /duplicate."""

    def test_duplicate_clones_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/repository/duplicate",
            json={"idwf": "test-01", "newidwf": "test-01-copy"},
            headers=session_headers,
        )
        assert resp.status_code == 200


class TestRepositoryDeleteModelProxy:
    """POST /admin/repository/delete/model — proxy to pybpm-api DELETE /delete."""

    def test_delete_removes_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/repository/delete/model",
            data={"idwf": "test-01"},
            headers=session_headers,
        )
        assert resp.status_code == 200


class TestRepositoryUpdateFolderProxy:
    """POST /admin/repository/update_folder — proxy to pybpm-api POST /update_folder."""

    def test_update_folder_moves_model(self, sync_test_client, session_headers):  # type: ignore[no-untyped-def]
        resp = sync_test_client.post(
            "/admin/repository/update_folder",
            json={"idwf": "test-01", "folder": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200

    def test_update_folder_accepts_form_encoded(
        self, sync_test_client, session_headers
    ):  # type: ignore[no-untyped-def]
        """Legacy Ext.Ajax sends params as form-encoded — should still work."""
        resp = sync_test_client.post(
            "/admin/repository/update_folder",
            data={"idwf": "test-01", "folder": "HR"},
            headers=session_headers,
        )
        assert resp.status_code == 200
