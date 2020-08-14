from . import Node, RedisEngine, FileEngine, gen_txo_key
from typing import List
from types import MethodType, FunctionType
import logging
import networkx as nx
import sys
import matplotlib

matplotlib.use('TkAgg')

import matplotlib.pyplot as plt

# 关闭 matplotlib 的日志
for name in logging.Logger.manager.loggerDict.keys():
    if name.startswith('matplotlib'):
        logging.getLogger(name).setLevel(logging.ERROR)


class Trace:
    def __init__(self,
                 min_height: int,
                 max_height: int,
                 init_txid: str = None,
                 init_address: str = None,
                 max_depth: int = 3,
                 debug: bool = False):
        """
        构建一个追溯实例
        :param min_height:   追溯的最小区块高度
        :param max_height:   追溯的最大区块高度
        :param init_txid:    追溯的初始 txid
        :param init_address: 追溯的初始地址，如果传入了 init_txid 则本参数无效
        :param max_depth:    追溯的深度，需要搜索的节点与追溯深度是指数关系，因此深度不要设置太大
        :param debug:        是否打印日志
        """

        assert isinstance(min_height, int), min_height
        assert isinstance(max_height, int), max_height
        assert min_height <= max_height, f'min_height {min_height} 不能大于 max_height {max_height}'
        assert sum(1 for i in [init_txid, init_address] if i) == 1, 'txid 和 address 只能输入一个'
        assert init_txid is None or isinstance(init_txid, str), init_txid
        assert init_address is None or isinstance(init_address, str), init_address
        assert isinstance(max_depth, int) and 0 <= max_depth < 100, '搜索深度 max_depth 只能是 0~99 的整数'
        assert isinstance(debug, bool), debug

        # 初始条件
        self.min_height = min_height  # 开始追溯的区块高度
        self.max_height = max_height  # 结束追溯的区块高度
        self.init_txid = init_txid  # 追溯的起始交易
        self.init_address = init_address  # 追溯的起始地址
        self.max_depth = max_depth  # 追溯的最大深度
        self.debug = debug  # 是否打印日志
        self.logger = logging.getLogger()

        sh = logging.StreamHandler(stream=sys.stdout)  # output to standard output
        sh.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(sh)
        self.logger.setLevel(logging.DEBUG)

        # 搜索引擎
        self.search_tx = None  # 查找单个交易的详情
        self.search_txo = None  # 查找单个交易输出的详情，包括该笔输出是否被消费以及被谁消费
        self.search_address = None  # 查找单个地址的详情
        # self.search_block = None
        self.batch_search_tx = None  # 批量查找交易详情
        self.batch_search_txo = None  # 批量查找交易输出的详情
        self.batch_search_address = None  # 批量查找地址详情
        # self.batch_search_block = None

        # 节点标签
        self.dict_label = {}  # 地址:标签 字典
        self.stop_labels = set()  # 停止追溯的标签

        # 追溯结果
        self.dict_cache_tx = {}  # 缓存的各笔交易详情
        self.dict_cache_txo = {}  # 缓存的各项交易输出
        self.init_nodes = []  # 追溯起始节点（如果是通过交易追溯的，则从交易的输出节点开始追溯，但交易本身还是会做可视化）
        self.edges = []  # 追溯过程中涉及到的节点与节点之间的交互：[(node1, node2, money), ...]

        # 各类节点字典： address -> node
        self.dict_middle_node = {}
        self.dict_normal_node = {}
        self.dict_multisig_node = {}
        self.dict_unknown_node = {}
        self.dict_return_node = {}

    def set_search_engine(self, engine: (FileEngine, RedisEngine)):
        """
        设置搜索引擎
        :param engine:
        :return:
        """
        assert isinstance(engine, (FileEngine, RedisEngine)), 'engine 需要是一个实例'
        assert hasattr(engine, 'get_txo'), 'engine 需要有 get_txo 方法'
        assert hasattr(engine, 'get_tx'), 'engine 需要有 get_tx 方法'
        assert hasattr(engine, 'get_address'), 'engine 需要有 get_address 方法'
        self.search_tx = engine.get_tx
        self.search_txo = engine.get_txo
        self.search_address = engine.get_address
        self.batch_search_tx = (engine.batch_get_tx if hasattr(engine, 'batch_get_tx')
                                else (lambda xs: [self.search_tx(x) for x in xs]))
        self.batch_search_txo = (engine.batch_get_txo if hasattr(engine, 'batch_get_txo')
                                 else (lambda xs: [self.search_tx(x) for x in xs]))
        self.batch_search_address = (engine.batch_get_address if hasattr(engine, 'batch_get_address')
                                     else (lambda xs: [self.search_tx(x) for x in xs]))
        return self

    def set_search_func(self,
                        *,
                        search_tx: (FunctionType, MethodType),
                        search_txo: (FunctionType, MethodType),
                        search_address: (FunctionType, MethodType),
                        batch_search_tx: (FunctionType, MethodType) = None,
                        batch_search_txo: (FunctionType, MethodType) = None,
                        batch_search_address: (FunctionType, MethodType) = None):
        """
        设置地址查找函数和交易查找函数
        :param search_tx:             查找单个交易的详情
        :param search_txo:            查找单个交易输出的详情，包括该笔输出是否被消费以及被谁消费
        :param search_address:        查找单个地址的详情
        :param batch_search_tx:       批量查找交易详情
        :param batch_search_txo:      批量查找交易输出的详情
        :param batch_search_address:  批量查找地址详情
        :return:
        """
        self.search_tx = search_tx
        self.search_txo = search_txo
        self.search_address = search_address
        self.batch_search_tx = batch_search_tx or (lambda xs: [self.search_tx(x) for x in xs])
        self.batch_search_txo = batch_search_txo or (lambda xs: [self.search_txo(x) for x in xs])
        self.batch_search_address = batch_search_address or (lambda xs: [self.search_address(x) for x in xs])
        return self

    def set_labels(self,
                   dict_label: dict = None,
                   stop_labels: (list, tuple, set) = None):
        """
        设置地址标签
        :param dict_label: 地址 -> 标签
        :param stop_labels: 停止追溯的标签列表
        :return:
        """
        self.dict_label = dict_label
        self.stop_labels = set(stop_labels)
        return self

    def reset(self):
        """
        重置追溯条件
        :return:
        """
        self.init_nodes = []  # 追溯起始节点（如果是通过交易追溯的，则从交易的输出节点开始追溯，但交易本身还是会做可视化）
        self.edges = []

        self.dict_middle_node = {}
        self.dict_normal_node = {}
        self.dict_multisig_node = {}
        self.dict_unknown_node = {}
        self.dict_return_node = {}

    def start(self):
        """
        开始追溯，追溯前先重置结果，然后按照输入条件开始追溯
        :return:
        """
        self.reset()  # 先重置

        if self.init_txid:
            # 获取交易数据并缓存
            tx = self.search_tx(self.init_txid)
            if not tx or tx['block_height'] < self.min_height or tx['block_height'] > self.max_height:
                self.init_nodes = []
            else:
                # 更新最低区块高度
                self.min_height = tx['block_height']
                # 更新缓存数据
                self.dict_cache_tx[self.init_txid] = tx
                dict_inputs = {i['key']: i for i in self.batch_search_txo(tx['inputs'])}
                self.dict_cache_txo.update(dict_inputs)
                keys = [gen_txo_key(tx['txid'], i) for i in range(tx['n_outputs'])]
                dict_outputs = {i['key']: i for i in self.batch_search_txo(keys)}
                self.dict_cache_txo.update(dict_outputs)
            self.init_nodes = self.progressing_tx(tx)
        elif self.init_address:
            self.init_nodes = [self.create_or_get_normal_node(self.init_address)]
        return self.__bfs()

    def __bfs(self):
        """
        广度优先追溯：
        1. 对于[节点列表] 里的每一个 [节点] ，找到它所有的 [ TXO ]
        2. 对于每一个 [ TXO ]，如果它还未被消费，则忽略；如果它被消费了，找到消费了它的 [ txid ]
        3. 对于每一个 [ txid ] ，找到 [交易详情]
        4. 处理该笔交易，获得该笔交易的所有 [输出节点列表] ，处理逻辑可见 self.progressing_tx 函数（所在区块高度不符合要求的交易在这一步被处理）
        5. 汇总每个节点、每笔交易的 [输出节点列表] ，作为 [下一轮搜索的节点列表] ，同时深度减一
        6. 循环上面的步骤，直到追溯的深度达到要求
        :return:
        """

        # 初始化
        next_nodes = self.init_nodes  # 下一轮搜索的节点
        marked_txid = {self.init_txid} if self.init_txid else set()  # 记录已经找过的交易
        marked_address = set([i.address for i in next_nodes])  # 记录已经找过的地址
        depth = 1  # 当前深度
        if self.debug:
            self.logger.info(f'第{depth}轮，搜索{len(next_nodes)}个节点')

        # 广度优先搜索
        while next_nodes and depth <= self.max_depth:
            # 第一步：获取所有地址详情
            addresses = [i.address for i in next_nodes]
            address_infos = self.batch_search_address(addresses)

            # 第二步：获取所有交易输出详情（满足被消费的条件）
            outputs = set()
            for info in address_infos:
                for key in info['outputs']:
                    outputs.add(key)
            dict_txo = {i['key']: i for i in self.batch_search_txo(outputs)}
            self.dict_cache_txo.update(dict_txo)

            # 第三步，获取所有花费了这些交易输出的交易
            txids = set([i['spent_txid'] for i in dict_txo.values()
                         if i['spent_txid'] and i['spent_txid'] not in marked_txid])
            marked_txid.update(txids)
            dict_tx = {i['txid']: i for i in self.batch_search_tx(txids)
                       if self.min_height <= i['block_height'] <= self.max_height}
            self.dict_cache_tx.update(dict_tx)
            # 额外添加一下这些交易的输入
            input_keys = sum([i['inputs'] for i in dict_tx.values()], [])
            dict_inputs = {i['key']: i for i in self.batch_search_txo(input_keys)}
            self.dict_cache_txo.update(dict_inputs)

            # 第四步，获得下一轮要处理的节点（满足没有被追溯过、且其标签不属于停止追溯的标签）
            next_nodes = set()
            for tx in dict_tx.values():
                next_nodes.update(set(i for i in self.progressing_tx(tx) if i.address not in marked_address))
            marked_address.update(set(i.address for i in next_nodes))
            next_nodes = set(i for i in next_nodes if self.dict_label.get(i) not in self.stop_labels)

            # 更新状态
            depth += 1
            if self.debug:
                self.logger.info(f'第{depth}轮，搜索{len(next_nodes)}个节点')
            # yield self.edges

        return self.edges

    def progressing_tx(self, tx: dict) -> List[Node]:
        """
        处理交易：
        1. 处理交易的输入，处理逻辑可见 self.progressing_inputs 函数文档，得到 [输入的节点列表]
        2. 处理交易的输出，处理逻辑可见 self.progressing_inputs 函数文档，得到 [输出的节点列表]
        3. 按 [输入的节点列表] 和 [输出的节点列表] 里的节点数量，分 [多对多]、[一对多(含一对一）]、[多对一] 这 3 种情况进行处理
        4. 特别地，对于 [多对多] 的情况，生成一个虚构的中间节点，使其变成 [多对一] 和 [一对多] 两种情况的组合
        5. 特别地，对于 [一对多] 和 [多对一] 这两种情况，通过 for 循环都使其变成多个 [一对一] 情况的组合
        6. 处理 [一对一] 的情况，处理逻辑可见 self.__one_2_one 函数
        :param tx:
        :return: 交易的输出节点列表
        """
        if not isinstance(tx, dict) or not self.min_height <= tx['block_height'] <= self.max_height:
            return []  # 区块高度不在指定范围内

        start_nodes, start_moneys = self.progressing_inputs(tx)
        end_nodes, end_moneys = self.progressing_outputs(tx)
        # 建立连接
        if len(start_nodes) > 1 and len(end_nodes) > 1:
            # 场景1：多个输入，多个输出，构造中间节点
            middle_node = self.create_or_get_middle_node(tx['txid'] + '_middle')
            middle_node.add_txid(tx['txid'])
            # 建立联系
            self.__many_2_one(start_nodes, start_moneys, middle_node)
            self.__one_2_many(middle_node, end_nodes, end_moneys)
        elif len(start_nodes) == 1:
            start_node = start_nodes[0]
            self.__one_2_many(start_node, end_nodes, end_moneys)
        elif len(end_nodes) == 1:
            end_node, end_money = end_nodes[0], end_moneys[0]
            self.__many_2_one(start_nodes, start_moneys, end_node)
            # 多对一的场景下，前面的地址转出的钱不是全部都到了后面的地址（还有手续费），因此还需要调整后面地址的余额
            fee = max(sum(i for i in start_moneys if i) - (end_money or 0), 0)
            end_node.balance -= fee
        elif len(start_nodes) > 1:
            # 多个输入地址，0 个输出地址
            if self.debug:
                self.logger.error(f'交易 {tx["txid"]} 具有多个输入地址，但是没有输出地址')
        elif len(end_nodes) > 1:
            # 0 个输入地址，多个输出地址
            if self.debug:
                self.logger.error(f'交易 {tx["txid"]} 具有多个输出地址，但是没有输入地址')
        else:
            # 0 个输入地址，0 个输出地址
            if self.debug:
                self.logger.error(f'交易 {tx["txid"]} 没有输入和输出地址')

        # 添加交易
        for start_node in start_nodes:
            start_node.add_txid(tx["txid"])
        for end_node in end_nodes:
            end_node.add_txid(tx["txid"])

        return end_nodes

    def __one_2_one(self, input_node: Node, output_node: Node, money: int):
        """
        一对一建立联系，包括：
        1. [输出节点] 记录 [转给它钱的地址] 以及 [转入金额]
        2. [输入节点] 记录 [转出钱的地址] 以及 [转出金额]
        3. 在 self.edges 里记录 [输入节点] 、 [输出节点] 、[转账金额]
        PS： 上面的 [转入金额] 、[转出金额] 、[转账金额] 是相同数额的钱
        :param input_node:
        :param output_node:
        :param money:
        :return:
        """
        output_node.add_in(input_node.address, money)
        input_node.add_out(output_node.address, money)
        self.edges.append((input_node.address, output_node.address, money))

    def __one_2_many(self, input_node: Node, output_nodes: List[Node], output_moneys: List[int]):
        """
        一对多建立联系
        :param input_node: 转出的节点
        :param output_nodes: 转入的节点列表
        :param output_moneys: 转入的金额列表，这里的金额是指实际收到的金额
        :return:
        """
        for output_node, money in zip(output_nodes, output_moneys):
            self.__one_2_one(input_node, output_node, money)

    def __many_2_one(self, input_nodes: List[Node], input_moneys: List[int], output_node: Node):
        """
        多对一建立联系
        :param input_nodes: 转出的节点列表
        :param input_moneys: 转出的金额列表，这里的金额是指实际花出去的金额
        :param output_node: 转入的节点
        :return:
        """
        for input_node, money in zip(input_nodes, input_moneys):
            self.__one_2_one(input_node, output_node, money)

    def progressing_inputs(self, tx: dict) -> (List[Node], List[int]):
        """
        批量处理输入：
        1. 对于每一笔 [交易的输入] ，找到对应的 [ TXO 详情]
        2. 通过 [ TXO 详情] 找到 [花费该笔 TXO 的地址]（对于数据缺失、多签等情况，生成虚构的地址）
        3. 通过 [花费该笔 TXO 的地址] 创建 [对应类型的节点]
        :return: 节点列表
        """
        assert isinstance(tx, dict), tx
        nodes, moneys = [], []
        for key in tx['inputs']:
            input_ = self.dict_cache_txo.get(key)
            if not input_ or len(input_['addresses']) == 0:
                # 如果是空字典，或者没有地址，则说明我们并没有获得交易输出的数据，因此用自定义的 address 虚构一个未知节点
                node = self.create_or_get_unknown_node(key)
            elif len(input_['addresses']) == 1:
                # 如果有 1 个地址，则说明是个普通类型的地址
                node = self.create_or_get_normal_node(input_['addresses'][0])
            else:
                # 如果有多个地址，则说明是个多签地址
                node = self.create_or_get_multisig_node(input_['addresses'])
            nodes.append(node)
            moneys.append(input_['value'])
        return nodes, moneys

    def progressing_outputs(self, tx: dict) -> (List[Node], List[int]):
        """
        批量处理输出：
        1. 通过 [交易的输出数量] 找到所有的 [ TXO 详情] （交易接口里并不返回具体的 TXO 详情，因为无论如何都要去搜索该笔 TXO 是否被消费）
        2. 对于每一个 [ TXO 详情] 找到 [收到该笔 TXO 入地址]（对于 OP_RETURN、多签等情况，生成虚构的地址）
        3. 通过 [花费该笔 TXO 的地址] 创建 [对应类型的节点]
        :return: 节点列表
        """
        assert isinstance(tx, dict), tx
        nodes, moneys = [], []
        for index in range(tx['n_outputs']):
            key = tx['txid'] + ',' + str(index)
            output = self.dict_cache_txo.get(key)
            if not output or output['value'] == 0:
                continue
            if len(output['addresses']) == 0:
                if output['type'] != 'OP_RETURN' and self.debug:
                    self.logger.error(f'交易 {tx["txid"]} 的第 {index} 笔输出异常：比特币不为 0 却没有地址')
                node = self.create_or_get_return_node(key)
            elif len(output['addresses']) == 1:
                node = self.create_or_get_normal_node(output['addresses'][0])
            else:
                node = self.create_or_get_multisig_node(output['addresses'])
            nodes.append(node)
            moneys.append(output['value'])
        return nodes, moneys

    def get_node(self, address: str) -> Node:
        """
        根据地址获取节点
        :param address:
        :return:
        """
        return (self.dict_normal_node.get(address)
                or self.dict_middle_node.get(address)
                or self.dict_multisig_node.get(address)
                or self.dict_unknown_node.get(address))

    def create_or_get_return_node(self, address: str) -> Node:
        """
        创建或获取用于销毁的独立地址
        :param address:
        :return:
        """
        if address not in self.dict_return_node:
            self.dict_return_node[address] = Node(address, address_type='return')
        return self.dict_return_node.get(address)

    def create_or_get_multisig_node(self, addresses: List[str]) -> Node:
        """
        创建或获取多重签名的独立地址
        :param addresses:
        :return:
        """
        assert isinstance(addresses, list) and len(addresses) > 1, addresses
        address = Node.generate_multisig_address(addresses)  # 生成新地址
        if address not in self.dict_multisig_node:
            self.dict_multisig_node[address] = Node(address, address_type='multisig', addresses=addresses)
        return self.dict_multisig_node.get(address)

    def create_or_get_middle_node(self, address: str) -> Node:
        """
        创建或获取中间节点
        :param address:
        :return:
        """
        assert isinstance(address, str)
        if address not in self.dict_middle_node:
            self.dict_middle_node[address] = Node(address, address_type='middle')
        return self.dict_middle_node.get(address)

    def create_or_get_unknown_node(self, address: str) -> Node:
        """
        创建或获取未知节点
        :param address:
        :return:
        """
        assert isinstance(address, str)
        if address not in self.dict_unknown_node:
            self.dict_unknown_node[address] = Node(address, address_type='unknown')
        return self.dict_unknown_node.get(address)

    def create_or_get_normal_node(self, address: str) -> Node:
        """
        创建或获取普通节点
        :param address:
        :return:
        """
        assert isinstance(address, str)
        if address not in self.dict_normal_node:
            self.dict_normal_node[address] = Node(address, address_type='normal')
        return self.dict_normal_node.get(address)

    def draw(self,
             min_weight: (int, float) = 10,  # 权重低于该值的边将被过滤
             min_weight_warning: (int, float) = None,  # 权重低于该值的边将显示普通的蓝色，高于该值的边将标红
             min_balance: (int, float) = 50,  # 余额低于该值的节点将不显示标签
             no_label_addresses: (list, tuple) = None,  # 在该列表中的地址将不显示标签
             ):
        """
        TODO 1: 应用 Elliptic 规则
        TODO 2: 动画化
        图中，每个节点代表了一个地址，每条有向的边代表了址 a -> 地址 b 的累计转账比特币（单位 btc）
        边将分为 3 个部分：要隐藏的边，显示为普通颜色的边，标红的边
        :param min_weight: 要展示的最小累计转账比特币，低于该值的边将隐藏
        :param min_balance: 要展示的最小余额，余额低于该值的节点将隐藏
        :param min_weight_warning: 需要突出显示的最小累计转账比特币，超过该值的边将变红色（最好比 min_weight 要大一些）
        :param no_label_addresses: 不显示标签的地址
        :return:
        """
        assert isinstance(min_weight, (int, float)), min_weight
        assert isinstance(min_balance, (int, float)), min_balance
        min_weight_warning = min_weight_warning or sys.maxsize
        assert isinstance(min_weight_warning, (int, float)), min_weight_warning

        # 过滤 edges
        edges = [[u, v, w / 1e8] for u, v, w in self.edges if w and w / 1e8 >= min_weight]
        if not edges:
            return

        # 第一步，构建网络
        graph = nx.DiGraph()
        graph.add_weighted_edges_from(edges)
        pos = nx.drawing.nx_agraph.graphviz_layout(graph)  # 布局('http://pygraphviz.github.io/')

        # 新的边和权重
        edges = [(u, v, d['weight']) for u, v, d in graph.edges(data=True)]
        weights = [i[2] for i in edges]
        max_weight = max(weights)

        # 第二步，预处理
        # 对节点按照类型分组，便于可视化时区分
        nodes = [self.get_node(i) for i in graph.nodes.keys()]
        nodes_actual = []
        nodes_middle = []
        for n in nodes:
            if n.type == 'middle':
                nodes_middle.append(n)
            else:
                nodes_actual.append(n)
        addresses_actual = [i.address for i in nodes_actual]
        addresses_middle = [i.address for i in nodes_middle]
        # 设置节点大小与要显示的标签（金额≥设定值、且类型不为中间节点）
        node_sizes_actual = [max(n.balance / 1e8, 1) for n in nodes_actual]
        node_sizes_middle = [max(n.balance / 1e8, 1) for n in nodes_middle]
        node_size_max = max(max(node_sizes_actual), max(node_sizes_middle))
        node_sizes_actual = [100 * (i / node_size_max) ** 0.1 for i in node_sizes_actual]  # 归一化再缩放，让小 size 的节点更大
        node_sizes_middle = [100 * (i / node_size_max) ** 0.1 for i in node_sizes_middle]
        node_size_mean = ((sum(node_sizes_actual) + sum(node_sizes_middle))
                          / (len(node_sizes_actual) + len(node_sizes_middle)))
        nodes_label = {n.address: self.dict_label.get(n.address, n.address + f'({n.balance / 1e8:.0f} BTC)')
                       for n in nodes_actual if n.balance / 1e8 >= min_balance and n.type != 'middle'}
        # 设置边标签，以及边与边标签的颜色与透明度（跟流转金额有关）
        edge_labels = {(u, v): f'{w:.0f}' for (u, v, w) in edges}
        # edge_labels_colors = {(u, v): 'r' if i >= min_weight_warning else 'b' for (u, v, w) in edges}
        edge_label_alphas = {(u, v): (w / max_weight) ** 0.5 for u, v, w in edges}
        edge_colors = ['r' if i >= min_weight_warning else 'b' for i in weights]
        edge_alphas = [(i / max_weight) ** 0.5 for i in weights]

        if self.debug:
            nodes.sort(key=lambda x: x.balance, reverse=True)
            for n in nodes:
                m = int(n.balance / 1e8)
                if m >= 0:
                    self.logger.info(f'地址 {n.address:>45s} 余额 {m:>5d} BTC')
                else:
                    break

        # 第三步，绘图
        plt.subplots(1, figsize=(18, 12), dpi=100)
        # 节点
        nx.draw_networkx_nodes(graph, pos, node_color="orange", node_size=node_sizes_actual, nodelist=addresses_actual)
        nx.draw_networkx_nodes(graph, pos, node_color="blue", node_size=node_sizes_middle, nodelist=addresses_middle)
        m_labels = nx.draw_networkx_labels(graph, pos, font_size=8, font_color='k', labels=nodes_label)
        no_label_addresses = set(no_label_addresses or [])
        if no_label_addresses:
            for address, text in m_labels.items():
                if address in no_label_addresses:
                    text.set_alpha(0)  # 透明度
        # 边
        m_edges = nx.draw_networkx_edges(graph, pos, node_size=node_size_mean, arrowstyle="->", arrowsize=10, width=2,
                                         edge_color=edge_colors, edge_cmap=plt.cm.Blues)
        for i, alpha in enumerate(edge_alphas):
            m_edges[i].set_alpha(alpha)  # 透明度

        # 边标签
        bbox = {'facecolor': 'none', 'edgecolor': 'none'}  # 去掉边框和背景色
        e_labels = nx.draw_networkx_edge_labels(graph, pos, font_color='blue', edge_labels=edge_labels, bbox=bbox)
        for key, text in e_labels.items():
            text.set_alpha(edge_label_alphas[key])  # 透明度
            # text.set_color(edge_labels_colors[key])  # 颜色

        pc = matplotlib.collections.PatchCollection(m_edges, cmap=plt.cm.Blues)
        pc.set_array(weights)
        plt.colorbar(pc)

        ax = plt.gca()
        ax.set_axis_off()
        plt.show()
