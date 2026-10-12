import json, os, sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import envcheck


@pytest.fixture
def proj(tmp_path):
    def w(name, text):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return str(p)
    w.dir = tmp_path
    return w


def test_parse_quotes_comments_export(proj):
    p = proj('.env', '# c\nA=1\nB="x # y"\nexport C=\'q\'\nD=v # note\nE=\n\nbad line\n1X=2\n')
    assert envcheck.parse_env(p) == {'A': '1', 'B': 'x # y', 'C': 'q', 'D': 'v', 'E': ''}


def test_parse_empty_file(proj):
    assert envcheck.parse_env(proj('.env', '')) == {}


def test_parse_invalid_utf8_raises(tmp_path):
    p = tmp_path / '.env'
    p.write_bytes(b'A=\xff\xfe\n')
    with pytest.raises(UnicodeDecodeError):
        envcheck.parse_env(str(p))


def test_check_full(proj):
    ex = proj('.env.example', 'A=1\nB=\nexport C="x # y"\n')
    env = proj('.env', 'A=1\nB=\nD=2\n')
    proj('app.py', 'import os\nos.environ["A"]; os.getenv("NEW_KEY")\n')
    r = envcheck.check(ex, env, [str(proj.dir)])
    assert r['missing_in_env'] == ['C']
    assert r['undocumented_in_env'] == ['D']
    assert r['empty_in_env'] == ['B']
    assert r['unused_in_code'] == ['B', 'C']
    assert 'NEW_KEY' in r['used_but_undocumented']


def test_check_without_env_file(proj):
    ex = proj('.env.example', 'A=1\n')
    r = envcheck.check(ex, str(proj.dir / 'nope'), [])
    assert r['missing_in_env'] == [] and r['unused_in_code'] == []


@pytest.mark.parametrize('src,name', [
    ('process.env.MY_VAR', 'MY_VAR'),
    ('process.env["MY_VAR"]', 'MY_VAR'),
    ('os.Getenv("MY_VAR")', 'MY_VAR'),
    ('ENV["MY_VAR"]', 'MY_VAR'),
    ('echo ${MY_VAR}', 'MY_VAR'),
    ('os.environ.get("MY_VAR")', 'MY_VAR'),
])
def test_usage_patterns(proj, src, name):
    proj('f.txt.js', src)
    assert name in envcheck.used_vars([str(proj.dir)])


def test_skips_ignored_dirs_and_extensions(proj):
    proj('node_modules/x.js', 'process.env.HIDDEN_VAR')
    proj('notes.txt', 'process.env.TXT_VAR')
    assert envcheck.used_vars([str(proj.dir)]) == set()


def test_unreadable_binary_source_ignored(tmp_path):
    (tmp_path / 'b.py').write_bytes(b'\xff\xfe\x00')
    assert envcheck.used_vars([str(tmp_path)]) == set()


def test_main_clean_exit_0(proj, capsys):
    ex = proj('.env.example', 'A=1\n')
    env = proj('.env', 'A=1\n')
    assert envcheck.main(['--example', ex, '--env', env]) == 0
    assert capsys.readouterr().out == ''


def test_main_problems_exit_1_text(proj, capsys):
    ex = proj('.env.example', 'A=1\nB=2\n')
    env = proj('.env', 'A=1\n')
    assert envcheck.main(['--example', ex, '--env', env]) == 1
    assert 'missing in env: B' in capsys.readouterr().out


def test_main_json(proj, capsys):
    ex = proj('.env.example', 'A=1\n')
    env = proj('.env', '')
    assert envcheck.main(['--example', ex, '--env', env, '--json']) == 1
    assert json.loads(capsys.readouterr().out)['missing_in_env'] == ['A']


def test_main_missing_example_exit_2(proj, capsys):
    assert envcheck.main(['--example', str(proj.dir / 'none')]) == 2
    assert 'not found' in capsys.readouterr().err


def test_main_bad_option_exit_2():
    with pytest.raises(SystemExit) as e:
        envcheck.main(['--bogus'])
    assert e.value.code == 2
