import logging
from urllib.parse import urlparse
import argparse

from .defaults import (
    SERVER_URL,
    SERVER_ADDR,
    SERVER_PORT,
    PEER_ADDR,
    PEER_PORT,
    RULES_DEFAULT,
    RULES_FILE,
    LOG_FORMAT,
    LOG_DATEFMT,
)
from .proxyserver import ProxyServer
from .proxydispatcher import ProxyDispatcher
from .rulematcher import RuleMatcher
from .connectors import (
    BaseConnector,
    WrappedConnector,
    TCPConnector,
    HTTPConnector,
)
from .acceptors import HTTPAcceptor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-s', '--server-url', default=SERVER_URL)
    parser.add_argument('-p', '--peer-urls', action='append', default=[])
    parser.add_argument('-D', '--rules-default', default=RULES_DEFAULT)
    parser.add_argument('-r', '--rules-file', default=RULES_FILE)
    args = parser.parse_args()

    debug = args.debug
    server_url = urlparse(args.server_url)
    server_addr = server_url.hostname or SERVER_ADDR
    server_port = server_url.port or SERVER_PORT
    peer_urls = args.peer_urls
    rules_default = args.rules_default
    rules_file = args.rules_file

    logging.basicConfig(level='DEBUG' if debug else 'INFO',
                        format=LOG_FORMAT,
                        datefmt=LOG_DATEFMT)
    rule_matcher = \
        RuleMatcher(rules_default=rules_default, rules_file=rules_file)
    rule_matcher.load_rules()
    connectors: list[BaseConnector] = []
    for url in peer_urls:
        peer_url = urlparse(url)
        peer_addr = peer_url.hostname or PEER_ADDR
        peer_port = peer_url.port or PEER_PORT
        wrapped_connector = WrappedConnector(base_connector=TCPConnector(),
                                             addr=peer_addr,
                                             port=peer_port)
        http_connector = HTTPConnector(base_connector=wrapped_connector)
        connectors.append(http_connector)
    proxy_dispatcher = \
        ProxyDispatcher(rule_matcher=rule_matcher, connectors=connectors)
    http_acceptor = HTTPAcceptor()
    proxy_server = \
        ProxyServer(acceptor=http_acceptor, dispatcher=proxy_dispatcher,
                    server_addr=server_addr, server_port=server_port)
    try:
        proxy_server.run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
