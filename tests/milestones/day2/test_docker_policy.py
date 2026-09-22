"""Security properties of the lab Docker API policy, without a Docker daemon."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "docker_policy", ROOT / "tools/mcp/day2/docker_read_proxy.py"
)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class DockerPolicyTests(unittest.TestCase):
    def test_caller_cannot_broaden_container_filter(self):
        route, kind = policy.allowed_route(
            "/v1.54/containers/json?all=1&filters={}&limit=999&size=1"
        )
        self.assertEqual(kind, "list")
        query = parse_qs(urlsplit(route).query)
        self.assertEqual(
            json.loads(query["filters"][0]),
            {"label": [f"com.docker.compose.project={policy.PROJECT}"]},
        )
        self.assertNotIn("size", query)

    def test_inspect_does_not_expose_environment_mounts_or_labels(self):
        raw = {
            "Id": "canary",
            "Name": "/lab",
            "Config": {
                "Tty": False,
                "Env": ["TOKEN=canary"],
                "Labels": {"private": "canary"},
            },
            "Mounts": ["private"],
            "State": {
                "Status": "running",
                "Running": True,
                "ExitCode": 0,
                "Error": "private",
            },
        }
        result = json.loads(
            policy.project_response(json.dumps(raw).encode(), "inspect")
        )
        self.assertEqual(result["Config"], {"Tty": False})
        self.assertNotIn("Mounts", result)
        self.assertNotIn("Error", result["State"])

    def test_container_list_is_projected_and_bounded(self):
        rows = [
            {
                "Id": str(i),
                "Names": ["/lab"],
                "Labels": {"TOKEN": "secret"},
                "Command": "secret",
            }
            for i in range(30)
        ]
        result = json.loads(policy.project_response(json.dumps(rows).encode(), "list"))
        self.assertEqual(len(result), 20)
        self.assertEqual(set(result[0]), {"Id", "Names"})

    def test_unrelated_routes_and_streams_denied(self):
        for route in (
            "/containers/other/logs",
            "/containers/create",
            "/images/json",
            "/events",
            "/info",
            "/containers/../version",
            "/containers/json?unknown=1",
            f"/containers/{policy.PROJECT}-debug-case-1/logs?follow=true",
            f"/containers/{policy.PROJECT}-debug-case-1/json?size=1",
        ):
            with self.subTest(route=route), self.assertRaises(PermissionError):
                policy.allowed_route(route)

    def test_logs_cannot_remove_bounds(self):
        route, kind = policy.allowed_route(
            f"/containers/{policy.PROJECT}-debug-case-1/logs?tail=all&follow=0"
        )
        self.assertEqual(kind, "logs")
        self.assertEqual(parse_qs(urlsplit(route).query)["tail"], ["100"])

    def test_id_requires_both_project_and_allowed_name(self):
        container_id = "a" * 64
        for project, name, permitted in (
            (policy.PROJECT, "debug-case", True),
            ("other", "debug-case", False),
            (policy.PROJECT, "postgres", False),
        ):
            with (
                self.subTest(project=project, name=name),
                patch.object(
                    policy,
                    "upstream",
                    return_value=json.dumps(
                        {
                            "Config": {
                                "Labels": {"com.docker.compose.project": project}
                            },
                            "Name": f"/{policy.PROJECT}-{name}-1",
                        }
                    ).encode(),
                ),
            ):
                if permitted:
                    route, _ = policy.allowed_route(f"/containers/{container_id}/logs")
                    self.assertIn(f"{policy.PROJECT}-debug-case-1", route)
                else:
                    with self.assertRaises(PermissionError):
                        policy.allowed_route(f"/containers/{container_id}/logs")

    def test_mutation_methods_share_explicit_denial(self):
        for method in ("POST", "DELETE", "PUT", "PATCH"):
            self.assertIs(getattr(policy.Handler, "do_" + method), policy.Handler.deny)

    def test_unavailable_engine_closes_connection(self):
        with patch.object(policy, "UnixConnection") as connection:
            connection.return_value.request.side_effect = OSError("engine unavailable")
            with self.assertRaises(OSError):
                policy.upstream("/version")
            connection.return_value.close.assert_called_once()

    def test_upstream_caps_bytes_and_closes_connection(self):
        with patch.object(policy, "UnixConnection") as connection:
            response = connection.return_value.getresponse.return_value
            response.status = 200
            response.read.return_value = b"x" * (policy.MAX_BYTES + 1)
            with self.assertRaises(ValueError):
                policy.upstream("/version")
            response.read.assert_called_once_with(policy.MAX_BYTES + 1)
            connection.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
