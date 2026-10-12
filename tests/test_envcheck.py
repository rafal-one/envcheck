import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import envcheck

class T(unittest.TestCase):
    def test_check(self):
        with tempfile.TemporaryDirectory() as d:
            def w(n, t):
                with open(os.path.join(d, n), 'w') as f:
                    f.write(t)
            w('.env.example', 'A=1\nB=\nexport C="x # y"\n')
            w('.env', 'A=1\nB=\nD=2\n')
            w('app.py', 'import os\nos.environ["A"]; os.getenv("NEW_KEY")\n')
            r = envcheck.check(os.path.join(d, '.env.example'), os.path.join(d, '.env'), [d])
            self.assertEqual(r['missing_in_env'], ['C'])
            self.assertEqual(r['undocumented_in_env'], ['D'])
            self.assertEqual(r['empty_in_env'], ['B'])
            self.assertEqual(r['unused_in_code'], ['B', 'C'])
            self.assertIn('NEW_KEY', r['used_but_undocumented'])
            self.assertEqual(envcheck.parse_env(os.path.join(d, '.env.example'))['C'], 'x # y')

unittest.main()
