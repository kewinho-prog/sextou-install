import os
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

    def real_checkout(self, commit=False):
        fixtures.write_exec(os.path.join(self.bin, 'git'), '#!/bin/sh\nexec /usr/bin/git "$@"\n')
        os.makedirs(self.core)
        self.git('init', '-q')
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
