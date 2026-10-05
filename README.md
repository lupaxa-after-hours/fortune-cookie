<p align="center">
  <a href="https://github.com/lupaxa-after-hours">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/organisations/after-hours/readme-logo.png" alt="After Hours" />
  </a>
</p>

<h1 align="center">Fortune Cookie</h1>

Draw a developer fortune: dubious wisdom, a warning, a prediction, or a joke
about Friday. The same package is a Python library and a command.

The PyPI name is `lupaxa-fortune-cookie`. The import path is `lupaxa.fortune`.
The console scripts are `fortune-cookie` and `lupaxa-fortune-cookie`. `lupaxa`
is a namespace package — there is no `lupaxa/__init__.py`.

Public names: `Fortune`, `FortuneGenerator`, `generate_fortune`,
`generate_fortunes`, `list_categories`, `Category`, `Mode`, `RiskLevel`,
`FortuneError`, `InvalidOptionError`, `UnknownCategoryError`, `DatasetError`,
`EmptyFortunePoolError`, `__version__`, `get_version()`.

Friday is a category you ask for. The tool does not look at the date, your
repository, or the network. Oracle lines are entertainment. They never run
commands.

## Install

```bash
pip install lupaxa-fortune-cookie
```

Requires Python 3.10+. The standard library is enough.

## CLI

```bash
fortune-cookie
fortune-cookie --category devops --count 3
fortune-cookie --dark
fortune-cookie --oracle --plain --no-numbers
fortune-cookie --seed 42
python -m lupaxa.fortune --category friday --plain
```

`lupaxa-fortune-cookie` is the same command. Decorative output is the default.
`--plain` drops the emoji and headings. Lucky numbers are on unless you pass
`--no-numbers`.

| Flag                | Meaning                                      |
| ------------------- | -------------------------------------------- |
| `--category`        | One ordinary category                        |
| `--count`           | How many fortunes to print (default 1)       |
| `--numbers`         | Show lucky numbers (the default)             |
| `--no-numbers`      | Hide lucky numbers                           |
| `--dark`            | Bleak fortunes                               |
| `--corporate`       | Jargon fortunes                              |
| `--oracle`          | A prediction, a risk, and an action          |
| `--plain`           | No emoji or headings                         |
| `--categories`      | List ordinary categories and exit            |
| `--seed`            | Repeat a result                              |
| `--version`         | Print `lupaxa-fortune x.y.z` and exit `0`    |
| `-h`, `--help`      | Show argparse help                           |

Special modes cannot be combined with each other or with `--category`.
`--categories` cannot be combined with generation options, including an
explicit `--count 1`.

A seed builds one `random.Random` for that invocation. Turning numbers off
skips a random draw, so the next fortune in a batch is not the one you would
have seen with numbers on. The same seed can also change between Python
releases, because it follows that version's random generator.

| Result              | Stdout                         | Exit  |
| ------------------- | ------------------------------ | ----- |
| Success             | One fortune block per result   | `0`   |
| `--version`         | `lupaxa-fortune x.y.z`         | `0`   |
| Invalid arguments   | argparse diagnostic            | `2`   |
| Broken dataset      | `lupaxa-fortune: error: ...`   | `1`   |
| Interrupted         | error on stderr                | `130` |

## Library

```python
import random
from lupaxa.fortune import FortuneGenerator, generate_fortune

fortune = generate_fortune(category="devops", rng=random.Random(42))
print(fortune.text)
print(fortune.lucky_numbers)

oracle = generate_fortune(mode="oracle", include_numbers=False, rng=random.Random(42))
print(oracle.risk_level, oracle.recommended_action)

generator = FortuneGenerator(rng=random.Random(42))
results = generator.generate_many(count=3, category="code")
```

Pass your own `random.Random` when a result must repeat. The library does not
call `random.seed()`.

| Call                                      | Return                    |
| ----------------------------------------- | ------------------------- |
| `generate_fortune()`                      | one standard fortune      |
| `generate_fortune(mode="oracle")`         | one oracle fortune        |
| `generate_fortunes(3, category="code")`   | three code fortunes       |
| `list_categories()`                       | the nine category names   |

| Situation                         | Result                    |
| --------------------------------- | ------------------------- |
| Unknown category                  | `UnknownCategoryError`    |
| Bad mode, count, or combination   | `InvalidOptionError`      |
| Bundled data is missing or wrong  | `DatasetError`            |

## Development

```bash
make init
make python-install-dev
make python-check
```

<a href="https://github.com/the-lupaxa-project">
    <img src="https://raw.githubusercontent.com/the-lupaxa-project/brand-assets/master/logos/components/footer-for-child-orgs.svg" alt="The Lupaxa Project Footer" width="100%" />
</a>
