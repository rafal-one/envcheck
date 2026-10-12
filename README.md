# envdiff

Single-file, zero-dependency tool that keeps `.env` and `.env.example` honest.
It reports variables missing from `.env`, undocumented ones, empty values,
documented-but-unused variables, and variables read in code (Python, JS/TS,
Ruby, Go, shell, YAML) but absent from `.env.example`. Exit code 1 on problems, so it fits CI and pre-commit.

```
python3 envdiff.py --example .env.example --env .env --src src --src scripts
python3 envdiff.py --json
```

Tests: `python3 tests/test_envdiff.py`

## License
MIT

## Support
If this saved you time: PayPal `4433@vp.pl`.

Donate: https://paypal.me/RafalBaranowski
