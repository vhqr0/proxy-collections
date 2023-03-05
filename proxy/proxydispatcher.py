import random
import logging

from .rulematcher import Rule, RuleMatcher
from .connectors import BaseConnector, NULLConnector, TCPConnector


class ProxyDispatcher:
    rule_matcher: RuleMatcher
    block_connector: NULLConnector
    direct_connector: TCPConnector
    forward_connectors: list[BaseConnector]

    logger = logging.getLogger('proxy_dispatcher')

    def __init__(self, rule_matcher: RuleMatcher,
                 connectors: list[BaseConnector]):
        self.rule_matcher = rule_matcher
        self.block_connector = NULLConnector(name='BLOCK')
        self.direct_connector = TCPConnector(name='DIRECT')
        if len(connectors) == 0:
            connectors.append(TCPConnector(name='FORWARD'))
            self.logger.warning('auto add forward connector')
        self.forward_connectors = connectors

    def dispatch(self, addr: str, port: int) -> BaseConnector:
        rule = self.rule_matcher.match(addr)
        connector: BaseConnector
        if rule == Rule.Block:
            connector = self.block_connector
        elif rule == Rule.Direct:
            connector = self.direct_connector
        else:
            connector = self.choice_forward_connector()
        self.logger.info('connect to %s %d via %s', addr, port, connector)
        return connector

    def choice_forward_connector(self) -> BaseConnector:
        if len(self.forward_connectors) <= 1:
            return self.forward_connectors[0]
        weights = [connector.weight for connector in self.forward_connectors]
        connector, = random.choices(self.forward_connectors, weights)
        return connector
