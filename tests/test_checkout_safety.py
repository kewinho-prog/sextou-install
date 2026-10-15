import os
import shutil
import shlex
import subprocess
import unittest
import test_bootstrap as fixtures


class CheckoutSafetyTest(unittest.TestCase):
    setUp = fixtures.BootstrapTestCase.setUp
    base_env = fixtures.BootstrapTestCase.base_env
    write_adaptativo = fixtures.BootstrapTestCase.write_adaptativo
    run_bootstrap = fixtures.BootstrapTestCase.run_bootstrap

    def git(self, *args):
        return subprocess.run(['/usr/bin/git', '-C', self.core, *args],
                              env={**self.base_env(), 'GIT_CONFIG_GLOBAL': '/dev/null',
                                   'GIT_CONFIG_NOSYSTEM': '1'}, check=True,
                              text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def real_checkout(self, commit=False, object_format=None):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node real obrigatório para testar integridade')
        fixtures.write_exec(os.path.join(self.bin, 'node'), '#!/bin/sh\nexec ' + shlex.quote(node) + ' "$@"\n')
        fixtures.write_exec(os.path.join(self.bin, 'git'), '#!/bin/sh\nexec /usr/bin/git "$@"\n')
        os.makedirs(self.core)
        self.git('init', '-q', *(['--object-format=' + object_format] if object_format else []))
        self.git('config', 'user.name', 'Synthetic test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/kewinho-prog/SextouCore.git')
        self.write_adaptativo()
        if commit:
            self.git('add', 'instalador')
            self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture')

    def assert_no_delegation(self):
        result = self.run_bootstrap([])
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'adapt_args.txt')))
        self.assertNotIn('--aplicar', result.stdout)

    def test_unborn_repository_never_executes_installer(self):
        self.real_checkout()
        self.assert_no_delegation()

    def test_modified_installer_is_preserved_without_execution(self):
        self.real_checkout(commit=True)
        path = os.path.join(self.core, 'instalador', 'instalar.sh')
        with open(path, 'a') as file:
            file.write('\n# user edit\n')
        with open(path, 'rb') as file:
            before = file.read()
        self.assert_no_delegation()
        with open(path, 'rb') as file:
            self.assertEqual(file.read(), before)

    def test_untracked_installer_never_executes(self):
        self.real_checkout()
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'fixture')
        self.assert_no_delegation()

    def test_clean_committed_checkout_keeps_preview_only_contract(self):
        self.real_checkout(commit=True)
        result = self.run_bootstrap(['--provedor', 'codex'])
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(os.path.join(self.tmp, 'adapt_args.txt')) as file:
            self.assertEqual(file.read().splitlines(), ['--adaptativo', '--provedor', 'codex'])

    def assert_hidden_edit_not_executed(self, flag, dependency=False):
        self.real_checkout(commit=True)
        relative = 'lib/hidden.mjs' if dependency else 'instalador/instalar.sh'
        path = os.path.join(self.core, relative)
        if dependency:
            os.makedirs(os.path.dirname(path))
            with open(path, 'w') as file:
                file.write('export const value = 1;\n')
            self.git('add', relative)
            self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'dependency fixture')
        self.git('update-index', flag, relative)
        with open(path, 'a') as file:
            file.write('\n# hidden synthetic edit\n' if not dependency else '// hidden synthetic edit\n')
        self.assertEqual(self.git('status', '--porcelain').stdout, '')
        with open(path, 'rb') as file:
            before = file.read()
        index_path = self.git('rev-parse', '--git-path', 'index').stdout.strip()
        if not os.path.isabs(index_path):
            index_path = os.path.join(self.core, index_path)
        with open(index_path, 'rb') as file:
            index_before = file.read()
        self.assert_no_delegation()
        with open(path, 'rb') as file:
            self.assertEqual(file.read(), before)
        with open(index_path, 'rb') as file:
            self.assertEqual(file.read(), index_before)

    def test_assume_unchanged_edit_is_preserved_without_execution(self):
        self.assert_hidden_edit_not_executed('--assume-unchanged')

    def test_skip_worktree_edit_is_preserved_without_execution(self):
        self.assert_hidden_edit_not_executed('--skip-worktree')

    def test_hidden_dependency_edit_is_not_executed(self):
        self.assert_hidden_edit_not_executed('--assume-unchanged', dependency=True)

    def test_unchanged_flags_do_not_block_valid_content(self):
        self.real_checkout(commit=True)
        for flag in ['--assume-unchanged', '--skip-worktree']:
            self.git('update-index', flag, 'instalador/instalar.sh')
            result = self.run_bootstrap([])
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_symlink_dependency_hidden_from_status_never_executes(self):
        self.real_checkout(commit=True)
        relative = 'lib/dependency.mjs'
        path = os.path.join(self.core, relative)
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as file:
            file.write('export const value = 1;\n')
        self.git('add', relative)
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture dependency')
        self.git('update-index', '--assume-unchanged', relative)
        outside = os.path.join(self.tmp, 'outside-dependency.mjs')
        with open(outside, 'w') as file:
            file.write('export const value = 1;\n')
        os.unlink(path)
        os.symlink(outside, path)
        self.assertEqual(self.git('status', '--porcelain').stdout, '')
        self.assert_no_delegation()
        self.assertTrue(os.path.islink(path))

    def test_sha256_checkout_keeps_preview_contract(self):
        self.real_checkout(commit=True, object_format='sha256')
        result = self.run_bootstrap([])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_utf8_and_space_in_tracked_path_keep_preview_contract(self):
        self.real_checkout(commit=True)
        path = os.path.join(self.core, 'lib', 'nome com espaço.mjs')
        os.makedirs(os.path.dirname(path))
        with open(path, 'w') as file:
            file.write('export const texto = "sintético";\n')
        self.git('add', 'lib')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'utf8 fixture')
        result = self.run_bootstrap([])
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_trailing_symlink_preserved(self, suffix):
        self.real_checkout(commit=True)
        outside = os.path.join(self.tmp, 'outside')
        link = os.path.join(self.tmp, 'destination-link')
        os.mkdir(outside)
        os.symlink(outside, link)
        # Redirect only clone to a real local Git fixture; never contact GitHub.
        fixtures.write_exec(os.path.join(self.bin, 'git'), """#!/bin/bash
while [[ "${1:-}" == "-c" ]]; do shift 2; done
if [[ "${1:-}" == "clone" ]]; then
  destination="${@: -1}"
  exec /usr/bin/git -c core.hooksPath=/dev/null clone --quiet "$SYNTHETIC_SOURCE" "$destination"
fi
exec /usr/bin/git "$@"
""")
        result = self.run_bootstrap([], env=self.base_env(
            SEXTOU_CORE=link + suffix, SYNTHETIC_SOURCE=self.core))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(os.listdir(outside), [], 'must refuse before clone writes through the symlink')
        self.assertTrue(os.path.islink(link))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'adapt_args.txt')))

    def test_symlink_with_one_trailing_slash_does_not_write(self):
        self.assert_trailing_symlink_preserved('/')

    def test_symlink_with_multiple_trailing_slashes_does_not_write(self):
        self.assert_trailing_symlink_preserved('///')

    def test_real_checkout_accepts_trailing_slashes(self):
        self.real_checkout(commit=True)
        result = self.run_bootstrap([], env=self.base_env(SEXTOU_CORE=self.core + '///'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, 'adapt_args.txt')))


if __name__ == '__main__':
    unittest.main()
