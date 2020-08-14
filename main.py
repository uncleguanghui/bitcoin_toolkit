from trace import FileEngine, RedisEngine, Trace

if __name__ == '__main__':
    """
    共读取到 289 个区块数据
    共解析出 743525 笔交易, 1222195 个地址, 2587198 个输入输出
    """

    min_height, max_height = 575012, 575300

    # # 设置基于字典的搜索引擎
    engine = FileEngine(
        dir_blocks='/Users/zhangguanghui/Library/Application Support/Bitcoin/blocks',
        min_height=min_height,
        max_height=max_height,
        index_cache='index_cache.pkl'
    )
    engine.read_data(show_progress=True)

    # 设置基于redis的搜索引擎
    engine = RedisEngine()
    engine.write_data(
        dir_blocks='/Users/zhangguanghui/Library/Application Support/Bitcoin/blocks',
        min_height=min_height,
        max_height=max_height,
        index_cache='index_cache.pkl',
        show_progress=True
    )

    trace = Trace(
        min_height=min_height,
        max_height=max_height,
        init_txid='e8b406091959700dbffcff30a60b190133721e5c39e89bb5fe23c5a554ab05ea',
        max_depth=4,
        debug=True
    ).set_search_engine(engine)
    trace.start()
    trace.draw(
        min_weight=50,  # 权重低于该值的边将被过滤
        min_weight_warning=200,  # 权重低于该值的边将显示普通的蓝色，高于该值的边将标红
        min_balance=50,  # 余额低于该值的节点将不显示标签
        no_label_addresses=None,  # 在该列表中的地址将不显示标签
    )

    # # 自定义
    trace.set_search_func(
        search_address=engine.get_address,
        search_tx=engine.get_tx,
        search_txo=engine.get_txo,
        batch_search_address=engine.batch_get_address,
        batch_search_tx=engine.batch_get_tx,
        batch_search_txo=engine.batch_get_txo
    )
