from datetime import datetime


class Block:
    def __init__(self,
                 block_hash: str,
                 *,
                 previous_hash: str = None,
                 height: int = None,
                 timestamp: datetime = None,
                 n_tx: int = None):
        assert isinstance(block_hash, str), block_hash
        assert previous_hash is None or isinstance(previous_hash, str), previous_hash
        assert height is None or isinstance(height, int), height
        assert timestamp is None or isinstance(timestamp, datetime), timestamp
        assert n_tx is None or isinstance(n_tx, int), n_tx
        self.hash = block_hash  # 区块 hash
        self.previous_hash = previous_hash  # 前一个区块 hash
        self.height = height  # 允许没有高度数据（场景：区块未排序）
        self.datetime = timestamp  # 挖矿时间
        self.n_tx = n_tx  # 交易数
        self.txid_list = []  # 交易 id 列表

    def __repr__(self):
        return f'Block({self.hash})' + (f'({self.height})' if self.height is not None else '')

    def add_txid(self, txid: str):
        """
        添加 txid
        :param txid:
        :return:
        """
        assert isinstance(txid, str), txid
        self.txid_list.append(txid)
