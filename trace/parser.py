from blockchain_parser.block import Block


def gen_txo_key(txid: str, index: (str, int)):
    """
    生成 txo 的 key
    :param txid:
    :param index:
    :return:
    """
    return str(txid) + ',' + str(index)


def parser_block(block: Block):
    # 交易数据
    dict_tx = {
        tx.txid: {
            "txid": tx.txid,
            "block_height": block.height,
            "is_coinbase": tx.is_coinbase(),
            "inputs": [gen_txo_key(input_.transaction_hash, input_.transaction_index) for input_ in tx.inputs],
            "n_outputs": tx.n_outputs,
        }
        for tx in block.transactions
    }

    # 获取输出和地址
    dict_output = {}
    dict_address = {}
    for tx in block.transactions:
        is_coinbase = tx.is_coinbase()
        # 处理输入
        for input_ in tx.inputs:
            key = gen_txo_key(input_.transaction_hash, input_.transaction_index)
            if key not in dict_output:
                dict_output[key] = {
                    "key": key,
                    "txid": input_.transaction_hash,
                    "index": input_.transaction_index,
                    "value": None,
                    "type": None,
                    "addresses": [],
                    "spent_txid": tx.txid,
                }
            else:
                dict_output[key]['spent_txid'] = tx.txid
        # 处理输出
        for index, output in enumerate(tx.outputs):
            if is_coinbase and index == 2:
                continue  # 跳过异常的输出
            key = gen_txo_key(tx.txid, index)
            dict_output[key] = {
                'key': key,
                "txid": tx.txid,
                "index": index,
                "value": output.value,
                "type": output.type,
                "addresses": list(set(i.address for i in output.addresses)),
                "spent_txid": None,
            }
            # 处理地址
            for address in output.addresses:
                if address.address not in dict_address:
                    dict_address[address.address] = {
                        "address": address.address,
                        "outputs": [key],
                        "labels": []
                    }
                else:
                    dict_address[address.address]['outputs'].append(key)

    return dict_tx, dict_address, dict_output
