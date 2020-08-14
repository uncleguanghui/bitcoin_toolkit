# 一个用于比特币追溯的框架

[toc]

# 简介
一个用于比特币追溯的框架

# 安装

```bash
pip install -r requirements.txt
```

# 教程

## 初始化数据

### 基于文件

```python
from trace import FileEngine

min_height, max_height = 575012, 575300

engine = FileEngine(
    dir_blocks='xxx/Bitcoin/blocks',
    min_height=min_height,
    max_height=max_height,
    index_cache='index_cache.pkl'
)

engine.read_data(show_progress=True)
```

### 基于 redis

```python
from trace import RedisEngine

min_height, max_height = 575012, 575300

engine = RedisEngine()

engine.write_data(
    dir_blocks='xxx/Bitcoin/blocks',
    min_height=min_height,
    max_height=max_height,
    index_cache='index_cache.pkl',
    show_progress=True
)
```

## 开始追踪

```python
from trace import Trace

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
```

# 高级

## 自定义搜索引擎

除了基于文件和基于 redis 的两种内置搜索引擎，还支持用户自定义。

只需要调用 `trace.set_search_func` 方法，将各函数传入即可。

`batch_` 的方法如果不传入的话，系统会自动用 for 循环调用单个查询函数。

```python
from trace import Trace

trace = Trace(
    min_height=min_height,
    max_height=max_height,
    init_txid='e8b406091959700dbffcff30a60b190133721e5c39e89bb5fe23c5a554ab05ea',
    max_depth=4,
    debug=True
)
trace.set_search_func(
    search_address=engine.get_address,
    search_tx=engine.get_tx,
    search_txo=engine.get_txo,
    batch_search_address=engine.batch_get_address,
    batch_search_tx=engine.batch_get_tx,
    batch_search_txo=engine.batch_get_txo
)
```