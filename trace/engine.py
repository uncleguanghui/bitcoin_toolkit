from typing import List
from blockchain_parser.blockchain import Block, Blockchain
from . import parser_block
import redis
import json
import sys
import os
import psutil


class FileEngine:
    def __init__(self,
                 dir_blocks: str,
                 min_height: int = None,
                 max_height: int = None,
                 index_cache: str = None,
                 show_warning: bool = True):
        """
        通过区块数据文件，构建基于字典的搜索引擎（适用于搜索的区块不太多的时候）
        :param dir_blocks: 全节点下 blocks 目录的路径
        :param min_height: 最低的区块高度
        :param max_height: 最高的区块高度
        :param index_cache: 整个区块索引的缓存路径，建议设置，下次可以不用再构建区块索引
        :param show_warning: 当读取数据太多的时候，显示告警
        """

        dir_blocks = str(dir_blocks)
        dir_index = os.path.join(dir_blocks, 'index')
        index_cache = str(index_cache)
        min_height = max(min_height or 0, 0)
        max_height = max(max_height or sys.maxsize, 0)
        assert os.path.exists(dir_blocks), f'路径 {dir_blocks} 不存在'
        assert os.path.exists(dir_index), f'路径 {dir_index} 不存在'
        assert isinstance(min_height, int), min_height
        assert isinstance(max_height, int), max_height
        assert 0 <= min_height <= max_height, f'min_height 不能大于 max_height'

        # 粗略地用 10 个区块和 50 个区块的数据估计了一下，平均每个区块的数据大概会占 0.8 M 左右的内存大小
        if show_warning:
            num_blocks = max_height - min_height + 1
            byte_cost_estimate = num_blocks * 0.8 * 1024 * 1024
            mem_total = float(psutil.virtual_memory().total)
            # 预估内存使用量超过系统内存 25% 后，发出警告（ 16GB 的内存建议读取的区块总数在 5000 个左右）
            if byte_cost_estimate > mem_total * 0.25:
                sys.stdout.write(F'系统总内存为 {mem_total:.3} GB，预读取的区块有 {num_blocks} 个，建议减少区块数量\n')
                sys.stdout.flush()

        # 解析所需的参数
        self.dir_blocks = dir_blocks
        self.dir_index = dir_index
        self.min_height = min_height
        self.max_height = max_height
        self.index_cache = index_cache

        # 存储的数据
        self.dict_address = {}
        self.dict_tx = {}
        self.dict_output = {}
        self.dict_block = {}

    def get_address(self, address: str) -> dict:
        """
        获取单个地址详情
        {
            "address": "address"               // 传入的地址
            "outputs": ["txid,index"],                   // 与该地址有关的所有交易输出（ txo ）
            "labels": ["label"]                // 地址标签
        }
        :param address:
        :return:
        """
        if isinstance(address, str):
            return self.dict_address.get(address)
        return {}

    def batch_get_address(self, addresses: List[str]) -> List[dict]:
        """
        批量获取地址详情
        :param addresses:
        :return:
        """
        return [self.get_address(i) for i in addresses]

    def get_tx(self, txid: str) -> dict:
        """
        获取单个交易详情
        {
            "txid": txid,                      // 传入的交易 id
            "block_height": "block_height",    // 区块高度
            "is_coinbase": is_coinbase,        // 是否是 coinbase 交易
            "inputs": ["txid,index"],          // 所有输入
            "n_outputs": n_outputs,            // 输出数
        }
        :param txid:
        :return:
        """
        if isinstance(txid, str):
            return self.dict_tx.get(txid)
        return {}

    def batch_get_tx(self, txids: List[str]) -> List[dict]:
        """
        批量获取交易详情
        :param txids:
        :return:
        """
        return [self.get_tx(i) for i in txids]

    def get_txo(self, key: str) -> dict:
        """
        获取单个输出详情，里面每个参数都很重要，例如 spent_txid 可以帮助我们了解到该笔输出有没有被消费掉
        {
            "key": "key",                      // key
            "txid": "txid",                    // 传入的交易 id
            "index": index,                    // 传入的输出位置
            "value": value,                    // 交易量（聪），可能为空（因为数据不全）
            "type": "type",                    // 交易类型, 约定如下 2 种特殊情况的类型取值为：多签 multisig ，销毁 OP_RETURN ，其他可以自定义
            "addresses": ["address"],          // 交易地址列表（一般只有一个地址，但多签时会有多个地址）
            "spent_txid": "spent_txid",        // 消费这笔输出的交易 id ，如果未被消费则为空
        }
        :param key: txid,index 构成的字符串
        :return:
        """
        if isinstance(key, str):
            return self.dict_output.get(key)
        return {}

    def batch_get_txo(self, keys: List[str]) -> List[dict]:
        """
        批量获取输出详情
        :param keys: ["txid,index", ... ]
        :return:
        """
        return [self.get_txo(i) for i in keys]

    # def get_block(self, block_hash: str) -> dict:
    #     """
    #     单个或批量获取区块详情
    #     {
    #         "block_hash": block_hash,          // 传入的区块 hash
    #         "height": height,                  // 区块高度
    #         "txid_list": [txid]                // 交易 id 列表
    #     }
    #     :param block_hash:
    #     :return:
    #     """
    #     if isinstance(block_hash, str):
    #         return self.dict_block.get(block_hash)
    #     return {}
    #
    # def batch_get_block(self, block_hashes: List[str]) -> List[dict]:
    #     """
    #     批量获取区块详情
    #     :param block_hashes:
    #     :return:
    #     """
    #     return [self.get_block(i) for i in block_hashes]

    def read_data(self, show_progress: bool = False):
        """
        从区块数据生成器里依次构建
        :param show_progress: 是否显示进度
        :return:
        """
        block_chain = Blockchain(self.dir_blocks)
        index = 0
        for i, block in enumerate(block_chain.get_ordered_blocks(index=self.dir_index, cache=self.index_cache)):
            if block.height < self.min_height:
                continue
            if block.height > self.max_height:
                break
            index += 1
            self.from_block(block)
            if show_progress:
                rate = index / (self.max_height - self.min_height + 1)
                sys.stdout.write(f'已完成 {rate * 100:.1f}% -- {index}/{self.max_height - self.min_height + 1}\r')
                sys.stdout.flush()

    def from_block(self, block: Block):
        """
        读取区块数据，并更新 self 里的几个字典
        :param block:
        :return:
        """
        dict_tx, dict_address, dict_output = parser_block(block)

        # 批量保存交易
        self.dict_tx.update(dict_tx)

        # 批量更新地址
        for key, info_new in dict_address.items():
            info_old = self.dict_address.get(key)
            if info_old:
                info_new['outputs'] = list(set(info_new['outputs'] + info_old['outputs']))
                info_new['labels'] = list(set(info_new['labels'] + info_old['labels']))
        self.dict_address.update(dict_address)

        # 批量更新输出
        for key, info_new in dict_output.items():
            info_old = self.dict_output.get(key)
            if info_old:
                info_new['spent_txid'] = info_new['spent_txid'] or info_old['spent_txid']
                info_new['value'] = info_new['value'] or info_old['value']
                info_new['type'] = info_new['type'] or info_old['type']
                info_new['addresses'] = info_new['addresses'] or info_old['addresses']
        self.dict_output.update(dict_output)


class RedisEngine:
    """
    自定义的 Redis 引擎
    """

    def __init__(self):
        super().__init__()
        self.pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True)
        self.redis = redis.Redis(connection_pool=self.pool)

    def get_address(self, address: str) -> dict:
        """
        获取单个地址详情，详情内容请见 FileEngine.get_address
        :param address:
        :return:
        """
        r = self.redis.get(address)
        return json.loads(r) if r else None

    def batch_get_address(self, addresses: List[str]) -> List[dict]:
        """
        批量获取地址详情，详情内容请见 FileEngine.get_address
        :param addresses:
        :return:
        """
        return [json.loads(r) if r else None for r in self.redis.mget(addresses)]

    def get_tx(self, txid: str) -> dict:
        """
        获取单个交易详情，详情内容请见 FileEngine.get_tx
        :param txid:
        :return:
        """
        r = self.redis.get(txid)
        return json.loads(r) if r else None

    def batch_get_tx(self, txids: List[str]) -> List[dict]:
        """
        批量获取交易详情，详情内容请见 FileEngine.get_tx
        :param txids:
        :return:
        """
        return [json.loads(r) if r else None for r in self.redis.mget(txids)]

    def get_txo(self, key: str) -> dict:
        """
        获取单个 txo 详情，详情内容请见 FileEngine.get_txo
        :param key:
        :return:
        """
        r = self.redis.get(key)
        return json.loads(r) if r else None

    def batch_get_txo(self, keys: List[str]) -> List[str]:
        """
        批量获取 txo 详情，详情内容请见 FileEngine.get_txo
        :param keys:
        :return:
        """
        return [json.loads(r) if r else None for r in self.redis.mget(keys)]

    # def get_block(self, block_hash: str) -> dict:
    #     """
    #     获取单个区块详情
    #     :param block_hash:
    #     :return:
    #     """
    #     r = self.redis.get(block_hash)
    #     return json.loads(r) if r else None
    #
    # def batch_get_block(self, block_hashes: List[str]) -> List[str]:
    #     """
    #     批量获取区块详情
    #     :param block_hashes:
    #     :return:
    #     """
    #     return [json.loads(r) if r else None for r in self.redis.mget(block_hashes)]

    def write_data(self,
                   dir_blocks: str,
                   min_height: int = None,
                   max_height: int = None,
                   index_cache: str = None,
                   show_progress: bool = False):
        """
        从区块数据里构建 4 种数据字典，并保存在 redis ，各字段含义见 FileEngine.__init__ 方法
        :param dir_blocks:
        :param min_height:
        :param max_height:
        :param index_cache:
        :param show_progress: 是否显示进度
        :return:
        """

        file_engine = FileEngine(dir_blocks, min_height, max_height, index_cache)
        file_engine.from_block = self.from_block  # 覆盖 FileEngine 的读取数据的函数
        file_engine.read_data(show_progress)
        return self

    def from_block(self, block: Block):
        """
        读取区块数据，并更新 redis 的数据
        :param block:
        :return:
        """
        dict_tx, dict_address, dict_output = parser_block(block)

        # 批量保存交易
        self.redis.mset({key: json.dumps(info) for key, info in dict_tx.items()})

        # 批量更新地址
        key_list = list(dict_address.keys())
        for key, j in zip(key_list, self.redis.mget(key_list)):
            info_old = json.loads(j) if j else None
            info_new = dict_address[key]
            if info_old:
                info_new['outputs'] = list(set(info_new['outputs'] + info_old['outputs']))
                info_new['labels'] = list(set(info_new['labels'] + info_old['labels']))
        self.redis.mset({key: json.dumps(info) for key, info in dict_address.items()})

        # 批量更新输出
        key_list = list(dict_output.keys())
        for key, j in zip(key_list, self.redis.mget(key_list)):
            info_old = json.loads(j) if j else None
            if info_old:
                info_new = dict_output[key]
                info_new['spent_txid'] = info_new['spent_txid'] or info_old['spent_txid']
                info_new['value'] = info_new['value'] or info_old['value']
                info_new['type'] = info_new['type'] or info_old['type']
                info_new['addresses'] = info_new['addresses'] or info_old['addresses']
        self.redis.mset({key: json.dumps(info) for key, info in dict_output.items()})
