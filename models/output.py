class Output:
    def __init__(self,
                 txid: str,
                 index: int,
                 *,
                 value: int = None,
                 output_type: str = None):
        assert isinstance(txid, str), txid
        assert isinstance(index, int), index
        assert value is None or isinstance(value, int), value
        assert output_type is None or isinstance(output_type, str), output_type
        self.txid = txid  # 产生这笔输出的交易 id
        self.index = index  # 在交易输出中的位置
        self.key = str(txid) + ',' + str(index)
        self.value = value  # 比特币，单位聪，如果为 None 就代表是根据 input 得到的，暂时不知道具体是多少
        self.type = output_type  # 输出类型
        self.addresses = []  # 作为输出的地址，一般只有一个地址，如果是多签的话会有对个地址
        self.spent_txid = None  # 花费这笔输出的 txid，为 None 则代表未消费（或者因数据不全，导致没有发现消费）

    def __repr__(self):
        return f'Output({self.key})'

    def add_address(self, address: str):
        """
        添加收到该笔输出的地址
        :param address:
        :return:
        """
        assert isinstance(address, str), address
        self.addresses.append(address)

    def set_spent(self, txid: str):
        """
        设置该笔输出的消费记录
        :param txid: 消费了该笔输出的 txid
        :return:
        """
        assert isinstance(txid, str), txid
        self.spent_txid = txid
