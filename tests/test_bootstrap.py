import os
import shutil
import stat
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALL_SH = os.path.join(REPO_ROOT, "install.sh")


def write_exec(path, content):
    with open(path, "w") as f:
        f.write(content)
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


FAKE_GIT = """#!/usr/bin/env bash
set -u
while [[ "${1:-}" == "-c" ]]; do shift 2; done
if [[ "$1" == "-C" ]]; then
  dir="$2"
  shift 2
  if [[ "$1" == "rev-parse" ]]; then echo true; exit 0; fi
  if [[ "$1" == "remote" && "$2" == "get-url" && "$3" == "origin" ]]; then
    if [[ -f "$dir/.git/remote-url" ]]; then
      cat "$dir/.git/remote-url"
      exit 0
    fi
    exit 1
  fi
  if [[ "$1" == "fetch" || "$1" == "merge" ]]; then
    : > "${FAKE_GIT_MUTATION_MARKER:-/dev/null}"
    exit 0
  fi
  exit 1
fi
if [[ "$1" == "clone" ]]; then
  shift
  args=()
  for a in "$@"; do
    case "$a" in
      --*) ;;
      *) args+=("$a") ;;
    esac
  done
  url="${args[0]}"
  dest="${args[1]}"
  if [[ "${FAKE_GIT_CLONE_FAIL:-0}" == "1" ]]; then
    exit 1
  fi
  mkdir -p "$dest/.git"
  printf '%s' "$url" > "$dest/.git/remote-url"
  exit 0
fi
exit 1
"""

FAKE_NODE = """#!/usr/bin/env bash
if [[ "${1:-}" == "-v" ]]; then
  echo "v${FAKE_NODE_VERSION:-24.0.0}"
  exit 0
fi
exit 0
"""

FAKE_GH = """#!/usr/bin/env bash
case "${1:-} ${2:-}" in
  "auth status")
    [[ "${FAKE_GH_AUTHED:-1}" == "1" ]] && exit 0 || exit 1 ;;
  "auth setup-git")
    exit 0 ;;
  "auth login")
    [[ "${FAKE_GH_LOGIN_OK:-1}" == "1" ]] && exit 0 || exit 1 ;;
  "repo view")
    [[ "${FAKE_GH_ACCESS:-1}" == "1" ]] && exit 0 || exit 1 ;;
esac
exit 1
"""


class BootstrapTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="sextou-boot-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.home = os.path.join(self.tmp, "home")
        os.makedirs(self.home)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        write_exec(os.path.join(self.bin, "git"), FAKE_GIT)
        write_exec(os.path.join(self.bin, "node"), FAKE_NODE)
        write_exec(os.path.join(self.bin, "gh"), FAKE_GH)
        self.core = os.path.join(self.tmp, "core")

    def base_env(self, **overrides):
        env = {
            "HOME": self.home,
            "PATH": self.bin + os.pathsep + "/usr/bin:/bin:/usr/sbin:/sbin",
            "SEXTOU_CORE": self.core,
            "FAKE_GH_AUTHED": "1",
            "FAKE_GH_ACCESS": "1",
            "FAKE_NODE_VERSION": "24.0.0",
        }
        env.update(overrides)
        return env

    def prepare_existing_checkout(self):
        os.makedirs(os.path.join(self.core, ".git"), exist_ok=True)
        with open(os.path.join(self.core, ".git", "remote-url"), "w") as f:
            f.write("https://github.com/kewinho-prog/SextouCore.git")

    def write_adaptativo(self, exit_code=0, args_out=None):
        path_dir = os.path.join(self.core, "instalador")
        os.makedirs(path_dir, exist_ok=True)
        args_out = args_out or os.path.join(self.tmp, "adapt_args.txt")
        content = (
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" > " + repr(args_out) + "\n"
            "exit " + str(exit_code) + "\n"
        )
        write_exec(os.path.join(path_dir, "instalar.sh"), content)
        open(os.path.join(path_dir, "instalar-adaptativo.mjs"), "w").close()
        return args_out

    def run_bootstrap(self, args, env=None, timeout=30):
        env = env if env is not None else self.base_env()
        return subprocess.run(
            ["bash", INSTALL_SH] + args,
            env=env,
            cwd=self.tmp,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
        )

    def test_preview_no_claude_codex(self):
        self.assertFalse(os.path.isdir(os.path.join(self.home, ".claude")))
        self.prepare_existing_checkout()
        self.write_adaptativo(exit_code=0)
        res = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("--provedor codex", res.stdout + res.stderr)
        self.assertFalse(os.path.isdir(os.path.join(self.home, ".claude")))

    def test_provider_injection_is_rejected_before_access(self):
        malicious = "Ana $(touch pwned_marker) ; rm -rf /tmp/should-not-happen"
        res = self.run_bootstrap(["--provedor", malicious], env=self.base_env(FAKE_GH_AUTHED="0"))
        self.assertEqual(res.returncode, 2, res.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "pwned_marker")))
        self.assertNotIn("login", res.stdout + res.stderr)

    def test_malformed_flag_missing_value(self):
        res = self.run_bootstrap(["--provedor"])
        self.assertNotEqual(res.returncode, 0)

    def test_malformed_flag_duplicate(self):
        res = self.run_bootstrap(["--provedor", "codex", "--provedor", "gemini"])
        self.assertNotEqual(res.returncode, 0)

    def test_malformed_flag_unknown(self):
        res = self.run_bootstrap(["--bogus"])
        self.assertNotEqual(res.returncode, 0)

    def test_malformed_flag_invalid_provider(self):
        res = self.run_bootstrap(["--provedor", "nope"])
        self.assertNotEqual(res.returncode, 0)

    def test_aplicar_rejected_here(self):
        res = self.run_bootstrap(["--aplicar"])
        self.assertNotEqual(res.returncode, 0)

    def test_node_old_version(self):
        env = self.base_env(FAKE_NODE_VERSION="18.0.0")
        res = self.run_bootstrap([], env=env)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("node", (res.stdout + res.stderr).lower())

    def test_node_missing(self):
        os.remove(os.path.join(self.bin, "node"))
        res = self.run_bootstrap([])
        self.assertNotEqual(res.returncode, 0)

    def test_existing_checkout_no_fetch_merge(self):
        self.prepare_existing_checkout()
        self.write_adaptativo(exit_code=0)
        marker = os.path.join(self.tmp, "mutation_marker")
        env = self.base_env(FAKE_GIT_CLONE_FAIL="1", FAKE_GIT_MUTATION_MARKER=marker)
        res = self.run_bootstrap([], env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse(os.path.exists(marker))

    def test_unexpected_nonempty_destination(self):
        os.makedirs(self.core)
        with open(os.path.join(self.core, "arquivo.txt"), "w") as f:
            f.write("algo do usuário")
        res = self.run_bootstrap([])
        self.assertNotEqual(res.returncode, 0)

    def test_symlink_ancestor_destination(self):
        real_target = os.path.join(self.tmp, "real_target")
        os.makedirs(real_target)
        link = os.path.join(self.tmp, "link")
        os.symlink(real_target, link)
        core = os.path.join(link, "core")
        env = self.base_env(SEXTOU_CORE=core)
        res = self.run_bootstrap([], env=env)
        self.assertNotEqual(res.returncode, 0)

    def test_repository_access_denied(self):
        env = self.base_env(FAKE_GH_ACCESS="0")
        res = self.run_bootstrap([], env=env)
        self.assertNotEqual(res.returncode, 0)

    def test_adaptive_installer_absent(self):
        res = self.run_bootstrap([])
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ADAPTIVE_INSTALLER_UNAVAILABLE", res.stdout + res.stderr)

    def test_delegated_failure_no_success_message(self):
        self.prepare_existing_checkout()
        self.write_adaptativo(exit_code=7)
        res = self.run_bootstrap([])
        self.assertEqual(res.returncode, 7)
        self.assertNotIn("Aplique de verdade", res.stdout)
        self.assertNotIn("--aplicar", res.stdout)

    def test_login_absent_noninteractive(self):
        env = self.base_env(FAKE_GH_AUTHED="0")
        res = self.run_bootstrap([], env=env)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("interativo", (res.stdout + res.stderr).lower())

    def test_empty_and_flag_values_rejected_before_access(self):
        for args in (["--provedor", "", "--provedor", "codex"], ["--provedor", "--aplicar"], ["--provedor", "codex claude"], ["--adaptativo"], ["--nome", "Ana"], ["--comando", "aurora"]):
            result = self.run_bootstrap(args, env=self.base_env(FAKE_GH_AUTHED="0"))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("ARGUMENTO_INVALIDO", result.stderr)
            self.assertNotIn("login", result.stdout + result.stderr)

    def test_remote_suffix_is_not_expected_repository(self):
        self.prepare_existing_checkout()
        self.write_adaptativo()
        with open(os.path.join(self.core, ".git/remote-url"), "w") as f:
            f.write("https://example.invalid/kewinho-prog/SextouCore.git")
        result = self.run_bootstrap([])
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--aplicar", result.stdout)

    def test_legacy_shell_without_adaptive_module_is_rejected(self):
        self.prepare_existing_checkout()
        self.write_adaptativo()
        os.unlink(os.path.join(self.core, "instalador/instalar-adaptativo.mjs"))
        result = self.run_bootstrap([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ADAPTIVE_INSTALLER_UNAVAILABLE", result.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "adapt_args.txt")))

    def test_malformed_node_version_is_rejected(self):
        result = self.run_bootstrap([], env=self.base_env(FAKE_NODE_VERSION="invalid"))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("login presente", result.stdout)

    def test_errors_use_stderr(self):
        result = self.run_bootstrap(["--desconhecida"])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("ARGUMENTO_INVALIDO", result.stderr)

    def test_cancelled_preview_never_prints_apply_command(self):
        self.prepare_existing_checkout()
        self.write_adaptativo(exit_code=130)
        result = self.run_bootstrap(["--provedor", "codex"])
        self.assertEqual(result.returncode, 130)
        self.assertIn("cancelada", result.stderr.lower())
        self.assertNotIn("--aplicar", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
