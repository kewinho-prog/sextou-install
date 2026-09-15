import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")
RELEASE_JSON = os.path.join(REPO_ROOT, "release.json")
REAL_GIT = shutil.which("git")
UNPUBLISHABLE_SOURCE_SHA = "NAO_PUBLICAR_ATE_COMMIT_A"


def write_exec(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    mode = os.stat(path).st_mode
    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def git(*args, cwd=None):
    return subprocess.run(
        [REAL_GIT, *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def verify_bootstrap_publication(repo_root=REPO_ROOT, manifest=None):
    """Fail closed unless release.json points at these exact install.sh bytes."""
    if manifest is None:
        with open(os.path.join(repo_root, "release.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)

    source_sha = manifest.get("BOOTSTRAP_SOURCE_SHA")
    bootstrap = manifest.get("bootstrap", {})
    publishable = bootstrap.get("publishable")
    source_status = bootstrap.get("source_sha_status")

    if publishable is False:
        if source_sha != UNPUBLISHABLE_SOURCE_SHA:
            raise AssertionError("BOOTSTRAP_UNPUBLISHABLE_MARKER_INVALID")
        if source_status != "replace_with_commit_a_full_sha":
            raise AssertionError("BOOTSTRAP_SOURCE_STATUS_INVALID")
        return

    if publishable is not True:
        raise AssertionError("BOOTSTRAP_PUBLISHABLE_FLAG_INVALID")
    if source_status != "verified_commit_a":
        raise AssertionError("BOOTSTRAP_SOURCE_STATUS_INVALID")
    if not isinstance(source_sha, str) or re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise AssertionError("BOOTSTRAP_SOURCE_SHA_INVALID")
    if REAL_GIT is None:
        raise AssertionError("GIT_REQUIRED_FOR_BOOTSTRAP_SOURCE_GATE")

    commit_exists = subprocess.run(
        [REAL_GIT, "-C", repo_root, "cat-file", "-e", f"{source_sha}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if commit_exists.returncode != 0:
        raise AssertionError("BOOTSTRAP_SOURCE_COMMIT_MISSING")

    is_ancestor = subprocess.run(
        [REAL_GIT, "-C", repo_root, "merge-base", "--is-ancestor", source_sha, "HEAD"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if is_ancestor.returncode != 0:
        raise AssertionError("BOOTSTRAP_SOURCE_NOT_ANCESTOR")

    committed_script = subprocess.run(
        [REAL_GIT, "-C", repo_root, "show", f"{source_sha}:install.sh"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if committed_script.returncode != 0:
        raise AssertionError("BOOTSTRAP_SOURCE_SCRIPT_MISSING")
    with open(os.path.join(repo_root, "install.sh"), "rb") as handle:
        current_script = handle.read()
    if committed_script.stdout != current_script:
        raise AssertionError("BOOTSTRAP_SOURCE_SCRIPT_DIVERGENT")


def verify_current_publication_gate():
    verify_bootstrap_publication()


FAKE_NODE = """#!/usr/bin/env bash
if [[ "${1:-}" == "-v" ]]; then
  printf 'v%s\\n' "${FAKE_NODE_VERSION:-24.21.0}"
  exit 0
fi
exit 0
"""


FAKE_UNAME = """#!/usr/bin/env bash
case "${1:-}" in
  -s) printf '%s\\n' "${FAKE_UNAME_S:-Darwin}" ;;
  -m) printf '%s\\n' "${FAKE_UNAME_M:-arm64}" ;;
  *)  printf '%s\\n' "${FAKE_UNAME_S:-Darwin}" ;;
esac
"""


FAKE_GH = """#!/usr/bin/env bash
if [[ -n "${FAKE_GH_LOG:-}" ]]; then
  printf '%s\\n' "$*" >> "$FAKE_GH_LOG"
fi
case "${1:-} ${2:-}" in
  "auth status") [[ "${FAKE_GH_AUTHED:-1}" == 1 ]] && exit 0 || exit 1 ;;
  "auth login") exit 97 ;;
  "repo view") [[ "${FAKE_GH_ACCESS:-1}" == 1 ]] && exit 0 || exit 1 ;;
esac
exit 1
"""


SYNTHETIC_INSTALLER = """#!/usr/bin/env bash
set -uo pipefail
provedor=""
aplicar=0
args=("$@")
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provedor) provedor="$2"; shift 2 ;;
    --aplicar) aplicar=1; shift ;;
    *) shift ;;
  esac
done
if [[ -n "${FAKE_CORE_UNSUPPORTED:-}" && "$provedor" == "$FAKE_CORE_UNSUPPORTED" ]]; then
  printf 'CONVERSA_AINDA_NAO_SUPORTADA\\n' >&2
  exit 42
fi
if [[ "${FAKE_CORE_CREATE_RACE_DESTINATION:-0}" == 1 ]]; then
  mkdir -p "$SEXTOU_CORE"
  printf 'concurrent owner\\n' > "$SEXTOU_CORE/concurrent.txt"
fi
if [[ "${FAKE_CORE_SWAP_PARENT_TO_SYMLINK:-0}" == 1 ]]; then
  staging_name="${BASH_SOURCE[0]%%/*}"
  mkdir -p "$FAKE_CORE_EXTERNAL_PARENT/$staging_name"
  printf 'external sentinel\\n' > "$FAKE_CORE_EXTERNAL_PARENT/$staging_name/sentinel.txt"
  mv "$FAKE_CORE_PARENT" "$FAKE_CORE_MOVED_PARENT"
  ln -s "$FAKE_CORE_EXTERNAL_PARENT" "$FAKE_CORE_PARENT"
fi
if [[ -n "${FAKE_CORE_ARGS_OUT:-}" ]]; then
  printf '%s\\n' "${args[@]}" > "$FAKE_CORE_ARGS_OUT"
fi
if (( aplicar == 1 )) && [[ -n "${FAKE_CORE_CONFIG_MARKER:-}" ]]; then
  : > "$FAKE_CORE_CONFIG_MARKER"
fi
printf 'CORE_PREVIEW:%s\\n' "${provedor:-sem-escolha}"
"""


LEGACY_REQUIRED_SHELL_FILES = (
    "instalador/mensagens.sh",
    "instalador/verificar-configuracao.sh",
    "lib/lock-legado.sh",
    "lib/estado.sh",
    "lib/identidade.sh",
)


class BootstrapTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if REAL_GIT is None:
            raise unittest.SkipTest("git is required for the offline synthetic repository")

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sextou-bootstrap-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = os.path.join(self.tmp, "home")
        self.bin = os.path.join(self.tmp, "bin")
        self.core = os.path.join(self.home, ".sextou", "core")
        self.source = os.path.join(self.tmp, "core-source")
        os.makedirs(self.home)
        os.makedirs(self.bin)
        write_exec(os.path.join(self.bin, "node"), FAKE_NODE)
        write_exec(os.path.join(self.bin, "uname"), FAKE_UNAME)
        write_exec(os.path.join(self.bin, "gh"), FAKE_GH)
        self.tag, self.sha = self.create_core_repository()

    def create_core_repository(self, include_adaptive=True):
        os.makedirs(self.source, exist_ok=True)
        git("init", "-q", cwd=self.source)
        git("config", "user.name", "Sextou Test", cwd=self.source)
        git("config", "user.email", "sextou-test@example.invalid", cwd=self.source)
        installer_dir = os.path.join(self.source, "instalador")
        os.makedirs(installer_dir, exist_ok=True)
        if include_adaptive:
            write_exec(os.path.join(installer_dir, "instalar.sh"), SYNTHETIC_INSTALLER)
            write_exec(os.path.join(installer_dir, "atualizar.sh"), "#!/usr/bin/env bash\nexit 0\n")
            with open(os.path.join(installer_dir, "instalar-adaptativo.mjs"), "w", encoding="utf-8") as handle:
                handle.write("// synthetic offline fixture\n")
            with open(os.path.join(self.source, "package.json"), "w", encoding="utf-8") as handle:
                json.dump({"name": "sextou-core", "version": "0.2.0-rc.2"}, handle)
                handle.write("\n")
            for relative_path in LEGACY_REQUIRED_SHELL_FILES:
                write_exec(os.path.join(self.source, relative_path), "#!/usr/bin/env bash\nexit 0\n")
        else:
            with open(os.path.join(self.source, "README.md"), "w", encoding="utf-8") as handle:
                handle.write("fixture without adaptive installer\n")
        git("add", ".", cwd=self.source)
        git("commit", "-q", "-m", "synthetic core", cwd=self.source)
        git("branch", "-M", "main", cwd=self.source)
        sha = git("rev-parse", "HEAD", cwd=self.source)
        tag = "v-test-rc.2"
        git("tag", tag, cwd=self.source)
        return tag, sha

    def base_env(self, **overrides):
        env = {
            "HOME": self.home,
            "PATH": self.bin + os.pathsep + "/usr/bin:/bin:/usr/sbin:/sbin",
            "SEXTOU_CORE": self.core,
            "SEXTOU_BOOTSTRAP_TEST_MODE": "1",
            "SEXTOU_BOOTSTRAP_TEST_REPO": self.source,
            "SEXTOU_BOOTSTRAP_TEST_TAG": self.tag,
            "SEXTOU_BOOTSTRAP_TEST_SHA": self.sha,
            "FAKE_NODE_VERSION": "24.21.0",
            "FAKE_UNAME_S": "Darwin",
            "FAKE_UNAME_M": "arm64",
        }
        env.update(overrides)
        return env

    def production_env(self, **overrides):
        env = self.base_env()
        for key in (
            "SEXTOU_BOOTSTRAP_TEST_MODE",
            "SEXTOU_BOOTSTRAP_TEST_REPO",
            "SEXTOU_BOOTSTRAP_TEST_TAG",
            "SEXTOU_BOOTSTRAP_TEST_SHA",
        ):
            env.pop(key, None)
        env.update(overrides)
        return env

    def run_bootstrap(self, args=None, env=None):
        return subprocess.run(
            ["bash", INSTALL_SH, *(args or [])],
            cwd=self.tmp,
            env=env or self.base_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            text=True,
        )

    def assert_error(self, result, code):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(code, result.stderr)

    def test_offline_preview_installs_exact_pin_and_update_refspec(self):
        args_out = os.path.join(self.tmp, "args.txt")
        config_marker = os.path.join(self.tmp, "config-written")
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(FAKE_CORE_ARGS_OUT=args_out, FAKE_CORE_CONFIG_MARKER=config_marker),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.core), self.sha)
        self.assertEqual(git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.core), "main")
        self.assertEqual(
            git("config", "--get-all", "remote.origin.fetch", cwd=self.core),
            "+refs/heads/main:refs/remotes/origin/main",
        )
        self.assertEqual(read_text(args_out).splitlines(), ["--adaptativo", "--provedor", "codex"])
        self.assertFalse(os.path.exists(config_marker))
        self.assertEqual(
            read_text(os.path.join(self.core, ".git", "sextou-bootstrap-complete")),
            "schema=1\nrepository=kewinho-prog/SextouCore\n",
        )
        self.assertIn(self.tag, result.stdout)
        self.assertIn(self.sha, result.stdout)
        self.assertIn("--adaptativo --aplicar --provedor codex", result.stdout)

    def test_prepared_checkout_can_fetch_and_fast_forward_main_offline(self):
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(result.returncode, 0, result.stderr)

        with open(os.path.join(self.source, "update.txt"), "w", encoding="utf-8") as handle:
            handle.write("future update\n")
        git("add", "update.txt", cwd=self.source)
        git("commit", "-q", "-m", "future update", cwd=self.source)
        future_sha = git("rev-parse", "HEAD", cwd=self.source)

        git("fetch", "origin", cwd=self.core)
        git("merge", "--ff-only", "origin/main", cwd=self.core)
        self.assertEqual(git("rev-parse", "HEAD", cwd=self.core), future_sha)

    def test_emitted_second_stage_can_apply(self):
        config_marker = os.path.join(self.tmp, "config-written")
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(result.returncode, 0, result.stderr)
        applied = subprocess.run(
            ["bash", os.path.join(self.core, "instalador", "instalar.sh"), "--adaptativo", "--aplicar", "--provedor", "codex"],
            env=self.base_env(FAKE_CORE_CONFIG_MARKER=config_marker),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertTrue(os.path.exists(config_marker))

    def test_existing_checkout_refuses_rerun_and_points_to_updater(self):
        installed = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(installed.returncode, 0, installed.stderr)
        updater_before = read_text(os.path.join(self.core, "instalador", "atualizar.sh"))
        gh_log = os.path.join(self.tmp, "gh.log")
        result = self.run_bootstrap(["--provedor", "codex"], self.production_env(FAKE_GH_LOG=gh_log))
        self.assert_error(result, "BOOTSTRAP_ALREADY_INSTALLED")
        self.assertIn("instalador/atualizar.sh", result.stderr)
        self.assertFalse(os.path.exists(gh_log))
        self.assertEqual(read_text(os.path.join(self.core, "instalador", "atualizar.sh")), updater_before)

    def test_git_and_tracked_updater_without_required_core_files_are_partial(self):
        os.makedirs(os.path.join(self.core, "instalador"), exist_ok=True)
        updater = os.path.join(self.core, "instalador", "atualizar.sh")
        write_exec(updater, "#!/usr/bin/env bash\nexit 0\n")
        git("init", "-q", cwd=self.core)
        git("config", "user.name", "Sextou Test", cwd=self.core)
        git("config", "user.email", "sextou-test@example.invalid", cwd=self.core)
        git("add", "instalador/atualizar.sh", cwd=self.core)
        git("commit", "-q", "-m", "interrupted copy", cwd=self.core)
        git("remote", "add", "origin", "https://github.com/kewinho-prog/SextouCore.git", cwd=self.core)

        gh_log = os.path.join(self.tmp, "gh.log")
        result = self.run_bootstrap(["--provedor", "codex"], self.production_env(FAKE_GH_LOG=gh_log))
        self.assert_error(result, "DESTINATION_OCCUPIED")
        self.assertTrue(os.path.isfile(updater))
        self.assertFalse(os.path.exists(gh_log))

    def test_expected_origin_and_complete_minimum_identify_existing_core(self):
        for relative_path in (
            "instalador/atualizar.sh",
            "instalador/instalar.sh",
            *LEGACY_REQUIRED_SHELL_FILES,
        ):
            write_exec(os.path.join(self.core, relative_path), "#!/usr/bin/env bash\nexit 0\n")
        with open(os.path.join(self.core, "package.json"), "w", encoding="utf-8") as handle:
            json.dump({"name": "sextou-core", "version": "0.1.9"}, handle)
            handle.write("\n")
        git("init", "-q", cwd=self.core)
        git("config", "user.name", "Sextou Test", cwd=self.core)
        git("config", "user.email", "sextou-test@example.invalid", cwd=self.core)
        git("add", ".", cwd=self.core)
        git("commit", "-q", "-m", "existing core", cwd=self.core)
        git("remote", "add", "origin", "https://github.com/kewinho-prog/SextouCore.git", cwd=self.core)

        gh_log = os.path.join(self.tmp, "gh.log")
        result = self.run_bootstrap(["--provedor", "codex"], self.production_env(FAKE_GH_LOG=gh_log))
        self.assert_error(result, "BOOTSTRAP_ALREADY_INSTALLED")
        self.assertFalse(os.path.exists(gh_log))

    def test_prima_installation_refuses_new_bootstrap(self):
        prima = os.path.join(self.home, ".prima", "core")
        os.makedirs(os.path.join(prima, "instalador"), exist_ok=True)
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assert_error(result, "LEGACY_PRIMA_INSTALLATION")
        self.assertIn(".prima/core/instalador/atualizar.sh", result.stderr)
        self.assertFalse(os.path.exists(self.core))

    def test_non_checkout_destination_is_preserved(self):
        os.makedirs(self.core)
        existing = os.path.join(self.core, "keep.txt")
        with open(existing, "w", encoding="utf-8") as handle:
            handle.write("do not replace\n")
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assert_error(result, "DESTINATION_OCCUPIED")
        self.assertEqual(read_text(existing), "do not replace\n")

    def test_tag_and_sha_divergence_never_executes_core(self):
        with open(os.path.join(self.source, "second.txt"), "w", encoding="utf-8") as handle:
            handle.write("second commit\n")
        git("add", "second.txt", cwd=self.source)
        git("commit", "-q", "-m", "second", cwd=self.source)
        other_sha = git("rev-parse", "HEAD", cwd=self.source)
        marker = os.path.join(self.tmp, "args.txt")
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(SEXTOU_BOOTSTRAP_TEST_SHA=other_sha, FAKE_CORE_ARGS_OUT=marker),
        )
        self.assert_error(result, "CORE_RELEASE_MISMATCH")
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(os.path.exists(self.core))

    def test_release_outside_main_never_executes_core(self):
        git("checkout", "-q", "-b", "release-only", cwd=self.source)
        with open(os.path.join(self.source, "release-only.txt"), "w", encoding="utf-8") as handle:
            handle.write("not integrated in main\n")
        git("add", "release-only.txt", cwd=self.source)
        git("commit", "-q", "-m", "release outside main", cwd=self.source)
        outside_sha = git("rev-parse", "HEAD", cwd=self.source)
        outside_tag = "v-outside-main"
        git("tag", outside_tag, cwd=self.source)
        git("checkout", "-q", "main", cwd=self.source)

        marker = os.path.join(self.tmp, "args.txt")
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(
                SEXTOU_BOOTSTRAP_TEST_TAG=outside_tag,
                SEXTOU_BOOTSTRAP_TEST_SHA=outside_sha,
                FAKE_CORE_ARGS_OUT=marker,
            ),
        )
        self.assert_error(result, "CORE_RELEASE_OUTSIDE_MAIN")
        self.assertFalse(os.path.exists(marker))
        self.assertFalse(os.path.exists(self.core))

    def test_missing_tag_has_no_remote_fallback(self):
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(SEXTOU_BOOTSTRAP_TEST_TAG="v-missing"),
        )
        self.assert_error(result, "CORE_RELEASE_NOT_FOUND")
        self.assertIn("main não será usado como versão alternativa", result.stderr)
        self.assertFalse(os.path.exists(self.core))

    def test_missing_adaptive_launcher_is_stable_and_leaves_no_checkout(self):
        shutil.rmtree(self.source)
        self.tag, self.sha = self.create_core_repository(include_adaptive=False)
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assert_error(result, "ADAPTIVE_INSTALLER_UNAVAILABLE")
        self.assertFalse(os.path.exists(self.core))

    def test_core_can_refuse_route_without_bootstrap_claim_or_write(self):
        config_marker = os.path.join(self.tmp, "config-written")
        result = self.run_bootstrap(
            ["--provedor", "claude"],
            self.base_env(FAKE_CORE_UNSUPPORTED="claude", FAKE_CORE_CONFIG_MARKER=config_marker),
        )
        self.assertEqual(result.returncode, 42)
        self.assertIn("CONVERSA_AINDA_NAO_SUPORTADA", result.stderr)
        self.assertIn("CORE_PREVIEW_FAILED", result.stderr)
        self.assertIn("somente o Core pode confirmar", result.stdout)
        self.assertFalse(os.path.exists(config_marker))
        self.assertFalse(os.path.exists(self.core))

    def test_atomic_destination_claim_refuses_directory_created_during_preview(self):
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(FAKE_CORE_CREATE_RACE_DESTINATION="1"),
        )
        self.assert_error(result, "DESTINATION_RACE")
        self.assertEqual(read_text(os.path.join(self.core, "concurrent.txt")), "concurrent owner\n")
        self.assertFalse(os.path.exists(os.path.join(self.core, ".git")))
        self.assertFalse(os.path.exists(os.path.join(self.core, "core")))
        self.assertEqual(os.listdir(self.core), ["concurrent.txt"])

    def test_parent_symlink_swap_preserves_external_sentinel_and_orphan_staging(self):
        parent = os.path.dirname(self.core)
        moved_parent = parent + "-original"
        external_parent = os.path.join(self.tmp, "external-parent")
        os.makedirs(external_parent)

        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(
                FAKE_CORE_SWAP_PARENT_TO_SYMLINK="1",
                FAKE_CORE_PARENT=parent,
                FAKE_CORE_MOVED_PARENT=moved_parent,
                FAKE_CORE_EXTERNAL_PARENT=external_parent,
            ),
        )
        self.assert_error(result, "PARENT_IDENTITY_CHANGED")
        self.assertTrue(os.path.islink(parent))
        staging_names = [name for name in os.listdir(moved_parent) if name.startswith(".sextou-bootstrap.")]
        self.assertEqual(len(staging_names), 1)
        staging_name = staging_names[0]
        external_staging = os.path.join(external_parent, staging_name)
        self.assertEqual(read_text(os.path.join(external_staging, "sentinel.txt")), "external sentinel\n")
        self.assertEqual(os.listdir(external_staging), ["sentinel.txt"])
        self.assertFalse(os.path.exists(os.path.join(external_parent, "core")))
        self.assertTrue(os.path.isdir(os.path.join(moved_parent, staging_name, "core", ".git")))
        self.assertFalse(
            os.path.exists(os.path.join(moved_parent, staging_name, "core", ".git", "sextou-bootstrap-complete"))
        )
        self.assertFalse(os.path.exists(os.path.join(moved_parent, "core")))

    def test_all_provider_names_reach_core_unchanged(self):
        providers = ("claude", "codex", "gemini", "opencode", "local", "codex-local")
        for index, provider in enumerate(providers):
            with self.subTest(provider=provider):
                destination = os.path.join(self.tmp, f"core-{index}")
                args_out = os.path.join(self.tmp, f"args-{index}.txt")
                result = self.run_bootstrap(
                    ["--provedor", provider],
                    self.base_env(SEXTOU_CORE=destination, FAKE_CORE_ARGS_OUT=args_out),
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(
                    read_text(args_out).splitlines(),
                    ["--adaptativo", "--provedor", provider],
                )
                self.assertIn("somente o Core pode confirmar", result.stdout)

    def test_node_23_and_25_are_refused(self):
        for version in ("23.11.0", "25.0.0"):
            with self.subTest(version=version):
                destination = os.path.join(self.tmp, "core-node-" + version)
                result = self.run_bootstrap(
                    ["--provedor", "codex"],
                    self.base_env(FAKE_NODE_VERSION=version, SEXTOU_CORE=destination),
                )
                self.assert_error(result, "NODE_VERSION_UNSUPPORTED")
                self.assertFalse(os.path.exists(destination))

    def test_only_homologated_node_24_patch_is_accepted(self):
        accepted = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(accepted.returncode, 0, accepted.stderr)

        destination = os.path.join(self.tmp, "core-other-patch")
        refused = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(FAKE_NODE_VERSION="24.21.1", SEXTOU_CORE=destination),
        )
        self.assert_error(refused, "NODE_VERSION_UNSUPPORTED")

    def test_node_20_is_refused_by_new_install_bootstrap(self):
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(FAKE_NODE_VERSION="20.19.5"),
        )
        self.assert_error(result, "NODE_VERSION_UNSUPPORTED")
        self.assertIn("devem seguir pelo atualizador", result.stderr)
        self.assertFalse(os.path.exists(self.core))

    def test_wrong_architecture_and_os_are_refused_before_clone(self):
        cases = (("Darwin", "x86_64"), ("Linux", "arm64"))
        for index, (system, machine) in enumerate(cases):
            with self.subTest(system=system, machine=machine):
                destination = os.path.join(self.tmp, f"platform-{index}")
                result = self.run_bootstrap(
                    ["--provedor", "codex"],
                    self.base_env(FAKE_UNAME_S=system, FAKE_UNAME_M=machine, SEXTOU_CORE=destination),
                )
                self.assert_error(result, "PLATFORM_UNSUPPORTED")
                self.assertFalse(os.path.exists(destination))

    def test_bootstrap_never_performs_login(self):
        gh_log = os.path.join(self.tmp, "gh.log")
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.production_env(FAKE_GH_AUTHED="0", FAKE_GH_LOG=gh_log),
        )
        self.assert_error(result, "GITHUB_LOGIN_REQUIRED")
        calls = read_text(gh_log).splitlines()
        self.assertEqual(calls, ["auth status"])
        self.assertFalse(os.path.exists(self.core))

    def test_access_denied_has_no_fallback_clone(self):
        gh_log = os.path.join(self.tmp, "gh.log")
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.production_env(FAKE_GH_ACCESS="0", FAKE_GH_LOG=gh_log),
        )
        self.assert_error(result, "CORE_ACCESS_DENIED")
        calls = read_text(gh_log).splitlines()
        self.assertEqual(calls[0], "auth status")
        self.assertTrue(calls[1].startswith("repo view kewinho-prog/SextouCore"))
        self.assertNotIn("auth login", "\n".join(calls))
        self.assertFalse(os.path.exists(self.core))

    def test_invalid_arguments_are_rejected_before_output_or_clone(self):
        cases = (
            ["--provedor"],
            ["--provedor", "invalid"],
            ["--provedor", "codex", "--provedor", "gemini"],
            ["--node-20-transicao"],
            ["--aplicar"],
            ["--nome", "Sexta"],
        )
        for args in cases:
            with self.subTest(args=args):
                result = self.run_bootstrap(args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("ARGUMENTO_INVALIDO", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(os.path.exists(self.core))

    def test_provider_shell_injection_is_data_and_rejected(self):
        marker = os.path.join(self.tmp, "pwned")
        result = self.run_bootstrap(["--provedor", f"codex; touch {marker}"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(marker))

    def test_symlink_destination_is_refused(self):
        target = os.path.join(self.tmp, "real")
        os.makedirs(target)
        link = os.path.join(self.tmp, "linked")
        os.symlink(target, link)
        result = self.run_bootstrap(
            ["--provedor", "codex"],
            self.base_env(SEXTOU_CORE=os.path.join(link, "core")),
        )
        self.assert_error(result, "DESTINATION_SYMLINK")

    def test_release_manifest_matches_shell_pin_and_contract(self):
        with open(RELEASE_JSON, encoding="utf-8") as handle:
            manifest = json.load(handle)
        with open(INSTALL_SH, encoding="utf-8") as handle:
            shell = handle.read()

        def shell_value(name):
            match = re.search(rf'^{name}="([^"]+)"$', shell, re.MULTILINE)
            self.assertIsNotNone(match, name)
            return match.group(1)

        self.assertEqual(manifest["core"]["repository"], shell_value("CORE_REPOSITORY"))
        self.assertEqual(manifest["release"], manifest["core"]["tag"])
        self.assertEqual(manifest["core"]["tag"], shell_value("CORE_RELEASE_TAG"))
        self.assertEqual(manifest["core"]["sha"], shell_value("CORE_RELEASE_SHA"))
        self.assertEqual(manifest["runtime"]["node_homologated"], shell_value("NODE_HOMOLOGATED"))
        self.assertEqual(
            manifest["providers"]["accepted"],
            ["claude", "codex", "gemini", "opencode", "local", "codex-local"],
        )
        self.assertFalse(manifest["providers"]["bootstrap_asserts_operational"])
        self.assertNotRegex(shell, r"(?m)^\s*gh auth login(?:\s|$)")
        self.assertNotRegex(shell, r"(?m)^\s*git (?:pull|merge)(?:\s|$)")
        self.assertIn("merge-base --is-ancestor", shell)

        source_sha = manifest["BOOTSTRAP_SOURCE_SHA"]
        verify_bootstrap_publication()
        docs = read_text(os.path.join(REPO_ROOT, "docs", "instalar-no-mac.md"))
        readme = read_text(os.path.join(REPO_ROOT, "README.md"))
        self.assertIn(source_sha, docs)
        self.assertIn(source_sha, readme)
        self.assertNotIn("sextou-install/main/install.sh", docs + readme + shell)


class PublicationGateTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if REAL_GIT is None:
            raise unittest.SkipTest("git is required for the publication gate")

    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sextou-publication-gate-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        git("init", "-q", cwd=self.tmp)
        git("config", "user.name", "Sextou Test", cwd=self.tmp)
        git("config", "user.email", "sextou-test@example.invalid", cwd=self.tmp)

    @staticmethod
    def manifest(source_sha, *, publishable=True, source_status="verified_commit_a"):
        return {
            "BOOTSTRAP_SOURCE_SHA": source_sha,
            "bootstrap": {
                "publishable": publishable,
                "source_sha_status": source_status,
            },
        }

    def commit_script(self, content):
        with open(os.path.join(self.tmp, "install.sh"), "wb") as handle:
            handle.write(content)
        git("add", "install.sh", cwd=self.tmp)
        git("commit", "-q", "-m", "bootstrap script", cwd=self.tmp)
        return git("rev-parse", "HEAD", cwd=self.tmp)

    def test_unpublished_marker_is_required_until_commit_a_exists(self):
        verify_bootstrap_publication(
            self.tmp,
            self.manifest(
                UNPUBLISHABLE_SOURCE_SHA,
                publishable=False,
                source_status="replace_with_commit_a_full_sha",
            ),
        )
        with self.assertRaisesRegex(AssertionError, "BOOTSTRAP_UNPUBLISHABLE_MARKER_INVALID"):
            verify_bootstrap_publication(
                self.tmp,
                self.manifest("0" * 40, publishable=False, source_status="replace_with_commit_a_full_sha"),
            )

    def test_nonexistent_source_commit_cannot_be_published(self):
        self.commit_script(b"#!/usr/bin/env bash\nexit 0\n")
        with self.assertRaisesRegex(AssertionError, "BOOTSTRAP_SOURCE_COMMIT_MISSING"):
            verify_bootstrap_publication(self.tmp, self.manifest("0" * 40))

    def test_source_script_must_match_current_bytes(self):
        source_sha = self.commit_script(b"#!/usr/bin/env bash\nprintf 'A\\n'\n")
        with open(os.path.join(self.tmp, "install.sh"), "wb") as handle:
            handle.write(b"#!/usr/bin/env bash\nprintf 'B\\n'\n")
        git("add", "install.sh", cwd=self.tmp)
        git("commit", "-q", "-m", "changed bootstrap script", cwd=self.tmp)
        with self.assertRaisesRegex(AssertionError, "BOOTSTRAP_SOURCE_SCRIPT_DIVERGENT"):
            verify_bootstrap_publication(self.tmp, self.manifest(source_sha))

    def test_source_commit_must_be_ancestor_of_head(self):
        source_sha = self.commit_script(b"#!/usr/bin/env bash\nexit 0\n")
        git("checkout", "-q", "--orphan", "unrelated", cwd=self.tmp)
        os.remove(os.path.join(self.tmp, "install.sh"))
        with open(os.path.join(self.tmp, "README.md"), "w", encoding="utf-8") as handle:
            handle.write("unrelated history\n")
        git("add", "-A", cwd=self.tmp)
        git("commit", "-q", "-m", "unrelated head", cwd=self.tmp)
        with self.assertRaisesRegex(AssertionError, "BOOTSTRAP_SOURCE_NOT_ANCESTOR"):
            verify_bootstrap_publication(self.tmp, self.manifest(source_sha))

    def test_unchanged_script_from_ancestor_commit_is_publishable(self):
        source_sha = self.commit_script(b"#!/usr/bin/env bash\nexit 0\n")
        with open(os.path.join(self.tmp, "release.json"), "w", encoding="utf-8") as handle:
            handle.write("{}\n")
        git("add", "release.json", cwd=self.tmp)
        git("commit", "-q", "-m", "release metadata", cwd=self.tmp)
        verify_bootstrap_publication(self.tmp, self.manifest(source_sha))


if __name__ == "__main__":
    unittest.main()
