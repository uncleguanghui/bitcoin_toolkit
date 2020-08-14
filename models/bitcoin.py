from . import Address, Transaction, Output, Block
from pathlib import Path


class Bitcoin:
    """
    比特币类，用于解析和记录数据
    """

    def __init__(self, dir_blocks: str):
        """
        初始化比特币类
        :param dir_blocks: xxx/Bitcoin/blocks
        """

        assert isinstance(dir_blocks, str) and Path(dir_blocks).exists(), f'路径 {dir_blocks} 不存在'
        self.dir_blocks = dir_blocks
        self.dict_block = {}
        self.dict_tx = {}
        self.dict_address = {}
        self.dict_output = {}

    def __repr__(self):
        return 'Bitcoin'

    @staticmethod
    def output_key(txid, index):
        return str(txid) + ',' + str(index)

    def create_or_get_address(self, address: str, **kwargs) -> Address:
        """
        创建或获取地址对象
        :param address:
        :param kwargs:
        :return:
        """
        assert isinstance(address, str), address
        if address not in self.dict_address:
            self.dict_address[address] = Address(address, **kwargs)
        return self.dict_address.get(address)

    def create_or_get_transaction(self, txid: str, **kwargs) -> Transaction:
        """
        创建或获取地址对象
        :param txid:
        :param kwargs:
        :return:
        """
        assert isinstance(txid, str), txid
        if txid not in self.dict_tx:
            self.dict_tx[txid] = Transaction(txid, **kwargs)
        return self.dict_tx.get(txid)

    def create_or_get_block(self, block_hash: str, **kwargs) -> Block:
        """
        创建或获取区块对象
        :param block_hash:
        :param kwargs:
        :return:
        """
        assert isinstance(block_hash, str), block_hash
        if block_hash not in self.dict_block:
            self.dict_block[block_hash] = Block(block_hash, **kwargs)
        return self.dict_block.get(block_hash)

    def create_or_get_input(self, key: str, spent_txid: str, **kwargs) -> Output:
        """
        创建或获取输入对象
        :param key: txid,index
        :param spent_txid:
        :param kwargs:
        :return:
        """
        assert isinstance(key, str), key
        assert isinstance(spent_txid, str), spent_txid
        input_ = self.create_or_get_output(key, **kwargs)
        if input_:
            input_.set_spent(spent_txid)
        return input_

    def create_or_get_output(self, key: str, **kwargs) -> Output:
        """
        创建或获取输出对象
        :param key: txid,index
        :param kwargs:
        :return:
        """
        assert isinstance(key, str), key
        if key not in self.dict_output:
            self.dict_output[key] = Output(key, **kwargs)
        return self.dict_output.get(key)
