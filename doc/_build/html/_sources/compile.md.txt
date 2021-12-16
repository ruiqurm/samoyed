# 编译

这里的编译与其说是编译，不如说是抽出语法树，并保存到模板上。执行时仍然是解释执行，而非二进制文件的执行。



## 命令行

在根目录下有一个`samc`。

这是一个python程序。

`samc`有两个模式：`run`,`gen`。

其中`run`执行解释操作，把文件解释执行。`gen`则生成一个新的文件。

### 解释执行

```
./samc run xxxx.sam
(或者 python ./samc xxxx.sam)
```

### 编译执行

编译执行可以指定输出文件名。未指定的话以输出文件名为`输入文件名+".py"`

```
./samc gen xxxx.sam
```

在当前路径下生成`xxxx.sam.py`

* 指定名称

```
./samc gen xxxx.sam -o a.py
```

在当前路径下生成`a.py`

