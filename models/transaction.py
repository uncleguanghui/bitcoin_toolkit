class Transaction:
    def __init__(self,
                 txid: str,
                 *,
                 block_hash: str = None,
                 is_coinbase: bool = False,
                 n_outputs: int = None):
        assert isinstance(txid, str), txid
        assert block_hash is None or isinstance(block_hash, str), block_hash
        assert isinstance(is_coinbase, bool), is_coinbase
        assert n_outputs is None or isinstance(n_outputs, int), n_outputs
        self.txid = txid  # 交易 id
        self.block_hash = block_hash  # 区块 hash ，可能为 None
        self.is_coinbase = is_coinbase  # 是否为 coinbase 交易，默认为 False ，可能不准
        self.inputs = []  # 输入，["txid,index", ...] ，准确
        self.n_outputs = n_outputs  # 输出数量，如果为 None 代表这笔交易是通过某笔交易的输入所发现的，可能不准

    def __repr__(self):
        return f'Transaction({self.txid})'

    def add_input(self, key: str):
        """
        为该笔交易添加输入
        :param key: txid,index
        :return:
        """
        assert isinstance(key, str), key
        self.inputs.append(key)
