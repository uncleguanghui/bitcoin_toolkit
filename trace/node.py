from typing import List


class Node:
    def __init__(self,
                 address: str,
                 *,
                 address_type: str = 'normal',
                 addresses: List[str] = None):
        """
        :param address: 节点地址
        :param address_type: 节点类型，有如下 4 种取值：
            1 ：normal（正常有地址的节点）
            2 ：middle (虚构的节点，用于多输入和多输出的场景下)
            3 ：multisig (多签地址)
            4 ：unknown (因数据缺失导致所有输入都无法解析出一个有效的地址，因此合并所有输入为一个地址)
            5 ：return (销毁比特币，该节点的类型是 OP_RETURN )
        :param addresses: 如果该节点类型是多签，那么需要传入转换前的地址列表
        """
        assert isinstance(address, str), address
        assert address_type in ['normal', 'middle', 'multisig', 'unknown', 'return'], address_type
        assert ((address_type != 'multisig' and addresses is None)
                or (address_type == 'multisig' or isinstance(addresses, list) and len(addresses) > 1)), addresses
        self.address = address
        self.type = address_type
        self.addresses = addresses
        self.in_money = {}  # address: money ：node 从不同地址收到的钱
        self.out_money = {}  # address: money ：node 转出去给不同地址的钱
        self.balance = 0  # 余额（不考虑追溯前的余额）
        self.tx_relative = set()  # 与该节点有关的 txid

    def __repr__(self):
        return f'Node_{self.type}_{self.address}'

    @staticmethod
    def generate_multisig_address(addresses: List[str]):
        """
        将多签地址转换成一个新地址
        :param addresses:
        :return:
        """
        assert isinstance(addresses, list), addresses
        return str(hash(','.join(addresses)))

    def add_in(self, address: str, money: int):
        """
        为当前节点添加前一个节点的地址，以及从前一个节点转账到当前节点的钱
        :param address:
        :param money: 转入的钱，允许为 None ，代表只知道转入了钱，但是不知道转入了多少（例如只知道 utxo 的 txid 和 index 但是不知道多少钱）
        :return:
        """
        assert isinstance(address, str), address
        assert money is None or isinstance(money, int), money
        # node 从不同地址收到的钱，允许为 None
        if address not in self.in_money or self.in_money[address] is None:
            # 如果一开始没有值，或者一开始传入的值也是 None，则重新赋值
            self.in_money[address] = money
        else:
            self.in_money[address] += money or 0
        self.balance += money or 0

    def add_out(self, address: str, money: int):
        """
        为当前节点添加后一个节点的地址，以及从当前节点转出到后一个节点的钱
        :param address:
        :param money: 转出的钱，允许为 None ，代表只知道转出了钱，但是不知道转出了多少（例如转出给一个虚构的中间节点）
        :return:
        """
        assert isinstance(address, str), address
        assert money is None or isinstance(money, int), money
        # node 转出去给不同地址的钱，允许为 None
        if address not in self.out_money or self.out_money[address] is None:
            # 如果一开始没有值，或者一开始传入的值也是 None，则重新赋值
            self.out_money[address] = money
        else:
            self.out_money[address] += money or 0
        self.balance -= money or 0

    def add_txid(self, txid: str):
        """
        添加交易 id
        :param txid:
        :return:
        """
        assert isinstance(txid, str), txid
        # 添加交易
        self.tx_relative.add(txid)
