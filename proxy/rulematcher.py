import os.path
import enum
import functools
import logging

from typing_extensions import Self
from typing import Optional

from .defaults import (
    RULES_DEFAULT,
    RULES_FILE,
)


class Rule(enum.Enum):
    Block = enum.auto()
    Direct = enum.auto()
    Forward = enum.auto()

    def __str__(self) -> str:
        if self is self.Block:
            return 'block'
        if self is self.Direct:
            return 'direct'
        if self is self.Forward:
            return 'direct'
        raise KeyError

    @classmethod
    def from_str(cls, s: str) -> Self:
        s = s.lower()
        if s == 'block':
            return cls(cls.Block)
        if s == 'direct':
            return cls(cls.Direct)
        if s == 'forward':
            return cls(cls.Forward)
        raise ValueError


class RuleMatcher:
    rules_default: Rule
    rules_file: str
    rules: Optional[dict[str, Rule]]

    logger = logging.getLogger('rule_matcher')

    def __init__(self,
                 rules_default: str = RULES_DEFAULT,
                 rules_file: str = RULES_FILE):
        self.rules_default = Rule.from_str(rules_default)
        self.rules_file = rules_file
        self.rules = None

    def load_rules(self):
        if not os.path.exists(self.rules_file):
            self.logger.warning('rules file not exists')
            return
        self.rules = dict()
        with open(self.rules_file) as f:
            for line in f:
                line = line.strip()
                if len(line) == 0 or line[0] == '#':
                    continue
                try:
                    rule, domain = line.split(maxsplit=1)
                    if domain not in self.rules:
                        self.rules[domain] = Rule.from_str(rule)
                except Exception as e:
                    self.logger.warning('except while loading rule %s: %s',
                                        line, e)

    @functools.cache
    def match(self, domain: str) -> Rule:
        if self.rules is None:
            return self.rules_default
        rule = self.rules.get(domain)
        if rule is not None:
            return rule
        sp = domain.split('.', 1)
        if len(sp) > 1:
            return self.match(sp[1])
        return self.rules_default
