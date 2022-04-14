# 因子测试框架

## 因子定义

因子定义可以结合Wind数据库完成，Wind数据库中保存有计算因子相关必需的数据，可以调用编写好的数据获取函数实现因子的计算。

本地计算完成的因子可以通过pandas读取的方式直接输入框架，但是数据必需满足如下的格式：

1. 因子名称必需作为列，一列代表一个因子
2. 因子数据的索引必需是双索引，第一维度索引名为name，第二维度索引名为asset；在第一个纬度上是所有的因子数据的日期，，第二维度上是个股/行业的名称
3. 因子数据如果要进行Barra回归计算，必需要携带一列名称为group的列（也正是这个原因，因子名称不能定义为group），表示各个asset所在的行业
4. 要进行回归，IC或是分层的计算，必须要保证数据带有未来收益，因此含有未来收益，因子值以及group行业的数据被称为标准数据

## 因子测试

因子测试的流程较为简单，主要是使用analyze中的三大函数进行测试，测试时除了Barra回归必需携带行业数据外，其他函数都不是必需携带行业数据的。使用如下：

```python
import dropbear as db

# get data
standarized_data = db.factor_datas_and_forward_returns('return_1m', ['2022-01-04', '2022-01-05'], forward_period=20)
# analyze them
analyzer = db.Analyzer(standarized_data)
reg_result = analyzer.regression()
ic_result = analyzer.ic()
layer_result = analyzer.layering()

# visulization
db.regression_plot(reg_result)
db.ic_plot(ic_result)
db.layering_plot(layer_result)
```

这里不只是通过db连接本地数据库获取到的因子数据可以放入Analyzer类，实际上，只要能够符合如下数据表的形式的数据，都可以作为Analyzer类的参数

1. 数据必须要是双索引的，第一维索引名称为`date`，放入的数据应该是时间类型的序列；第二位数据名为`asset`，放入的数据应当是资产的代码
2. 数据必须包含多列，为一个数据框(dataframe)，必须包含因子列与未来收益列，且这两种列数量可以不唯一，即可以有多列因子也可以有多列未来收益
3. 如果想要进行回归，必须要包含一列名称为`group`列，这一列的内容则是每个asset对应的行业
4. 如果需要进行持有收益图像的绘制，Analyzer会认为传入数据为持仓股，自动寻找名称包含`weight`的列，同时查找与未来收益相关的列，计算每一个weight在每一种未来收益下的持有收益，并更新出每一次调仓时的净值与累计净值

如下是一个可供参考的传入Analyzer的数据框

| date(index) | asset(index) | factor1 | factor2 | 1m | 3m | equal_weight | market_value_weight |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 2020-01-01 | 000001.SZ | 0.4 | 0.5 | -0.11 | -0.3 | 0.10 | 0.14 |
|  | 000002.SZ | 0.3 | 0.4 | 0.12 | 0.4 | 0.10 | 0.13 |
|  | 000003.SZ | 0.2 | 0.1 | 0.13 | 0.4 | 0.10 | 0.12 |
|  | 000004.SZ | 0.1 | -0.5 | 0.04 | 0.4 | 0.10 | 0.11 |
|  | 000005.SZ | 0.4 | 0.3 | 0.08 | 0.4 | 0.10 | 0.10 |
| 2020-01-02 | 000001.SZ | 0.4 | 0.5 | -0.11 | -0.3 | 0.10 | 0.14 |
|  | 000002.SZ | 0.3 | 0.4 | 0.12 | 0.4 | 0.10 | 0.13 |
|  | 000003.SZ | 0.2 | 0.1 | 0.13 | 0.4 | 0.10 | 0.12 |
|  | 000004.SZ | 0.1 | -0.5 | 0.04 | 0.4 | 0.10 | 0.11 |
|  | 000005.SZ | 0.4 | 0.3 | 0.08 | 0.4 | 0.10 | 0.10 |

## TODO

- 对输入数据进行约束，变成双行索引与双列索引的标准化数据，同时添加构造函数，更加方便、精确的控制输入的数据
- 加入机器学习算法至analyze中，可以使用机器学习的回归与分类方法进行计算