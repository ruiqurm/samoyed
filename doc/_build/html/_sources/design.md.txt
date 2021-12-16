# 设计与实现

## 词法分析和语法分析

`samoyed`使用`lark`的`lair`语法分析器解析代码。

[`lark`](https://lark-parser.readthedocs.io/en/latest/) 是一个现代的python解析库，lark可以解析任何上下文无关文法。

使用`lark`一方面是避免重复造轮子，减少工作量；直接使用`EBNF`描述文法能更灵活地拓展DSL的文法。

关于详细的EBNF文法，可以参考[文档](EBNF.md)

## `core.Interpreter`
解释器是项目的核心。

### 初始化

解释器初始化时，如果外部传入的是代码，会使用解析器解析得到语法树。

然后，解释器会建立一个上下文。上下文中包括一些内置的函数、外部传入的变量和解释器状态的信息。

建立完上下文后，扫描一遍生成好的语法树，并确认所有的state和入口state(`main`)。对于*外部的语句*，解释器会直接将其执行。

### 执行语句

可执行的语句有以下几种：

* `simple_stmt` 简单的语句，包括:

  * 赋值
  * 跳转表达式
  * pass表达式
  * 普通表达式

*  `if_stmt` 

  if语句

* `match_stmt`

   包括普通的match和可以控制输入时间的match

#### `simple_stmt`

对于`simple_stmt`，其语法分析结果类似下面：

```
simple_stmt
|
expr 
|
...
```

其中的赋值语句也类似，只是有两边：

```
assign_expr
   |
┌───┬─────┐
var =    expr
```

因此只需要判断一下类型，然后调用计算表达式即可。

####  `if_stmt` 

```
    if_stmt
        |
┌───────┬─────────┐
expr  true_st false_st
```

首先计算expr的值，然后根据结果去执行`true_st`或者`false_st`。这里迭代块中的语句，递归调用执行即可。

#### `match_stmt`

match有两种形式

第一种形式是**带有时间控制**的匹配
其中，@的第一个参数是超时时间，必选；第二个参数是最少持续时间，可选；
@后应该接入一个函数调用。延时表达式会不断调用这个函数

```
match @(10,2)funcall :
	compare_expr =>
		stat
	...
	silence =>
		stat
```
这种形式下，语法树大概是这样的：

```
            match_stmt
                 |
        ┌─────────────────────────────────┬────────────┬─────────────┐
        expr0                          match_case1  match_case..  silence
        |                                 |                          |
        ┌────────┬─────────┐         ┌────┬──────┐                 ┌────┐
        at_para func    func_para   expr1 stmt1  ...              stmt1  ...
```

这种形式下，假定func是会**一直产生值**的。（当然，即使没产生也有响应机制防止其无限阻塞）

这里会开启一个循环，每当func有新的值产生，就会进行一轮判断。如果有匹配，就执行值并结束匹配。

这里支持子串匹配和正则表达式匹配。可以见[语法参考](lang_ref.md)。其具体实现只是多加了一层类型判断，并对对应类型比较和匹配。

第二种形式是普通的多值匹配

```
match expr :
	compare_expr =>
		stat
	compare_expr =>
		stat
	default =>
		stat	
```

这个顺序比较即可，也不再赘述。

### 计算表达式

表达式是一个树状的结构，这里和执行语句类似，采用的是递归式的方法。

如果传入的是一个终结符（叶子节点），那么提取出值返回即可。这里比较特殊的是变量。如果是一个变量则需要查询上下文。

如果传入的是一些常量，直接返回即可（为什么会有常量呢，因为语法分析的时候还做了简单的语法制导，一些叶子节点被直接压缩成值）

如果传入的是一棵树。

判断它的类型，如果是简单的二元运算或者一元运算，例如：

* 三目表达式
* 逻辑非
* 比较运算
* 正负号

那么直接操作即可。

如果涉及到多个符号的，例如：

* 逻辑与
* 逻辑或
* 四则运算

那么使用reduce函数进行运算。

这里四则运算使用的reduce和一般的reduce不太一样，它是形如下面的结构的：

```
[1,+,2,-,3]或者[1,*,2,//,3]
```

一种比较函数式的想法是用交换x,y的方式：

```
def reduce(x, y):
    if callable(x):
        return x(y)
    else:
        return partial(y, x)
```

这里没有采用这种形式，而是用另一种比较易懂的形式：

```
for i in range(1, n, 2):
    """
    从1开始，步长为2，每次应该都要取到函数
    """
    op = l[i]
    operand2 = l[i + 1]
    sum = op(sum, operand2)
```

## `libs.TimeControl`

这个类用于控制超时和最早允许退出的时间。

这个类可以产生生成器实例，它的基本用法如下：

```python
t = TimeControl(input,5)
for i in t():
    # i 是每次获取的结果
    # 判断i....
    if 判断成功:
        t.cancel() # 关掉两个计时器
        break
```

其中t是一个生成器函数。



它主要有三个工具成员

* `max_wait_timer`
* `min_wait_timer`
* `watch_dog`

前两者主要用于监控最大和最小时间，而第三者用于中断传入的函数。因为传入的函数可能因为阻塞永远无法唤醒。

### `watch_dog`

`watch_dog`是一个装饰器。采用的内部信号唤醒的机制：

```python
def _handle_timeout(signum, frame):
	raise SamoyedTimeout(f"Timeout for function '{func.__name__}'")
signal.signal(signal.SIGALRM, _handle_timeout)
signal.setitimer(signal.ITIMER_REAL, seconds)
do_something...
# 如果超时了，会调用_handle_timeout，继而抛出一个异常
```

利用这个机制，我们将超时的程序中断。

### `timer`

`timer`是一个普通的计时线程。当超过一个时间时，它会调用构造时传入的函数。利用这个机制，我们可以知道什么时候超时了。

* 为什么需要两个超时？

  主要是一开始使用的是线程计时，后面发现信号计时的效果似乎也不错。信号计时可能会造成多级异常，因此这里没有采用两个信号计时

### 函数体

* 外层的try只用于处理`KeyboardInterrupt`，无其他用途
* 每次取完数据，判断是否已经超时；超时则退出
* `time.sleep`防止空转。

```python
# 外层的try只用于处理KeyboardInterrupt，无其他用途
try:
    while True:
        # 尝试执行函数
        result = None
        try:
            result = timeout_on_interval(*args, **kwargs)
        except SamoyedTimeout:
            # 如果超时，返回None
            yield None
        except EOFError:
            yield result
        except Exception as e:
            raise SamoyedRuntimeError(str(e))
        else:
            # 否则，返回结果
            yield result

        # 如果函数执行时间已经超时，那么退出
        if self.timeout.is_set():
            self.cancel()
            return

        # 睡眠，防止频繁运行
        time.sleep(self.sleep_interval)

except KeyboardInterrupt:
    self.cancel()
    raise KeyboardInterrupt
```

