"""Which build-store settings reach the evaluator sandbox."""

from __future__ import annotations

import contextlib
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

from nixbot.build_run import _with_build_store
from nixbot.config import BuildStoreConfig
from nixbot.nix_eval import EvalSettings

from .test_workload_identity import change_event, make_issuer

if TYPE_CHECKING:
    from pathlib import Path


async def eval_settings(tmp_path: Path, store: BuildStoreConfig) -> EvalSettings:
    o: Any = SimpleNamespace(
        config=SimpleNamespace(store_for=lambda *, external: store),  # noqa: ARG005
        identity_issuer=make_issuer(tmp_path),
    )
    build: Any = SimpleNamespace(id_=1, external=False)
    async with contextlib.AsyncExitStack() as stack:
        return await _with_build_store(
            o,
            change_event(pr_number=7),
            build,
            EvalSettings(gc_roots_dir=tmp_path / "gcroots"),
            stack,
        )


async def test_eval_stays_local_by_default(tmp_path: Path) -> None:
    # Evaluation runs the repository's code, which could read a token
    # handed to it and leak the store's write access.
    settings = await eval_settings(
        tmp_path, BuildStoreConfig(url="grpc://farm:50051", oidc_audience="farm")
    )
    assert settings.build_store_url is None
    assert settings.build_store_token_file is None


async def test_eval_in_store_opt_in(tmp_path: Path) -> None:
    settings = await eval_settings(
        tmp_path,
        BuildStoreConfig(
            url="grpc://farm:50051", oidc_audience="farm", eval_in_store=True
        ),
    )
    assert settings.build_store_url == "grpc://farm:50051"
    assert settings.build_store_token_file is not None
