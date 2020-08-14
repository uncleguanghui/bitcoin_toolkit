class Address:
    def __init__(self,
                 address: str,
                 *,
                 address_type: str = None):
        assert isinstance(address, str), address
        assert address_type is None or isinstance(address_type, str), address_type
        self.address = address  # 地址
        self.type_ = address_type  # 类型
        self.outputs = []  # 相关的输出（包括多签），[(txid, index), ...]
        self.money_in_with_multisig = 0  # 在观察窗口里，多签的收入
        self.money_in_without_multisig = 0  # 在观察窗口里，非多签的收入
        self.money_spent_with_multisig = 0  # 在观察窗口里，多签的支出
        self.money_spent_without_multisig = 0  # 在观察窗口里， 非多签的支出

    def __repr__(self):
        return f'Address({self.address})'

    def add_output(self, txid: str, index: int):
        """
        添加相关的输出，包括多签情况
        :param txid:
        :param index:
        :return:
        """
        assert isinstance(txid, str), txid
        assert isinstance(index, int), index
        self.outputs.append((txid, index))
