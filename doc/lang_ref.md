# 语法参考
## 基本类型
脚本语言支持以下基本类型
* bool
* int
* double
* str
* function  
* None

在一些特殊的式子中，可以使用
* 正则表达式`\...\ `
### 变量
#### 普通变量
* 和大多数语言一样，变量可以是中文字符，大小写字符，数字，和下划线(`_`)的组合，但是变量不允许由数字开头。  
一个更精确的表达如下：
```BNF
CN_ZH_LETTER: /[\u4e00-\u9fa5]/
LETTER: UCASE_LETTER | LCASE_LETTER | CN_ZH_LETTER
NAME : ("_"|LETTER) ("_"|LETTER|DIGIT)*
```

* 变量不需要声明即可使用。
#### 作用域
与大多数语言不同，这里变量没有作用域。如果出现重名会产生覆盖的问题。
#### $变量
命令行传参和正则表达式结果可以通过$轻松获得。  
##### 命令行传参
命令行传参只能在编译后的文件上传入。  
首先需要通过`arg_seq_add`和`arg_option_add`显式地定义参数。

```
arg_seq_add("arg1") ## 第一个顺序参数
arg_seq_add("arg2") ## 第二个
arg_option_add("option","o") ## --option 或者 -o
```
这样，编译运行后，我们就可以通过$快速访问这些变量。  
例如，对于`arg1`，你可以通过`$1`或者`$arg1`取得；
对于`arg2`，你可以通过`$2`或者`$arg2`取得；  
对于`option`，可以通过`$option`取得，

##### 正则表达式
正则表达式主要用于匹配数据。在完成匹配后，会把结果绑定到`$mg0`,`$mg1`..上面。  
其中`$mg`的个数取决于正则表达式组的个数。
比如，下面的正则表达式匹配浮点数。
```
/(\d+).(\d+)/
匹配3.14
$mg0 = 3.14
$mg1 = 3
$mg2 = 14
```
注意，由于只有一个作用域，`$mg`的结果不会被清空掉。第二次匹配发生时，可能仍能访问到之前的结果。  
此外，如果有参数名字叫`$mg`，那么编译器会报错
##### 其他
目前只绑定了`$PWD`。这是程序运行的路径

### 字符串

和python类似，支持单行字符串，也支持`"""`构成的多行字符串

### 注释

和python类似，使用`#`作为注释



## 运算符

`samoyed`支持大多数基本运算
### 符号
支持正负号
如果对字符串，None添加负号会报错
### 四则运算
支持`+`,`-`,`*`,`/`,`//`,`%`运算
### 逻辑运算
支持`and`,`or`,`not`
### 三目表达式
三目表达式的形式比较接近c++
```
bool_expr?expr1:expr2
```
### 运算符优先级

| 优先级（越小越高） | 符号                                 | 结合性   |
| ------------------ | ------------------------------------ | -------- |
| 0                  | `括号()`,`function`                  | -        |
| 1                  | 正负号                               | -        |
| 2                  | 乘除法，模(`%`)运算                  | 从左到右 |
| 3                  | 加减法                               | 从左到右 |
| 4                  | 比较符号(`>`,`>=`,`<`,`<=`,`=`,`!=`) | -        |
| 5                  | `not`运算                            |          |
| 6                  | `and`运算                            | 从左到右 |
| 7                  | `or`运算                             | 从左到右 |
| 8                  | 三目表达式                           | 从左到右 |



## 语句
### 块和缩进
`samoyed`和python的块缩进规则类似。
```
state a:
    pass
state b:
    if c:
        if d:
            pass
```
下面的缩进是错误的：
```
state a:
    speak(1)
   speak(2)
```
同样也支持将tab转换成空格。默认tab转换为4个空格。
### state语句 
state是`samoyed`的基本组成部分。  
state可以看成是有限状态机的声明。  
一个有效的程序，最外层除了**简单语句**，就是state语句。其中，简单语句会在开始执行前就被**全部执行**，无论它在前面还是后面。  
这里简单语句指的是赋值语句或者表达式。
例如：
```
a = 1
state main:
    speak(a)
a += 1
```
结果会是a=2
#### main
每一个程序必须要有一个起始状态。这里main就是唯一的起始状态。  
如果缺少main，解释器会报错  
### if语句
和python语言的if类似：
```
if expr :
    do_some_thing
    
## 或者
if expr:
    do
else:
    do_other
```
### pass
简单的占位功能
### branch
跳转语句   
使用方法是`branch a_state`  
例如：
```
state A:
    branch B
state B:
    branch C
state C:
    pass
```
如果`a_state`不存在，会抛出异常。  
对于一个state，当它执行完所有语句时，如果没有branch，那么它会默认退出。例如这里的`state C`

branch和goto类似。

如果branch在复杂语句(比如`match`,`if`)，它也会马上执行跳转

```
state A:
    if expr:
        speak("A")
        branch B
        speak("B")

```
将会打印`A`.
### match语句
`match`语句有两种用法。第一种用法是`switch`类似，第二种用法则带有时间控制。
#### 普通匹配match
这种match的格式是：
```
match expr:
    expr1 =>
        statement1    
    expr2 =>
        statement2
    ...
    default =>
        statement
```
`match`只会触发一次.并且采用顺序匹配。
##### branch缩写
对于branch语句，允许简写成：
```
expr1 => branch A
```
##### 子串
每个case的判断条件如果是字符串，且被判断的表达式也是字符串，那么不需要完全匹配，只需要case字符串是被判断字符串的子串即可。
例如：
```
match "hello world":
     "hello" =>
        speak("1")
     "world" =>
        speak("2")
     default =>
        speak("3")
```
输出`1`.  
注意`match`只会触发一次.并且采用顺序匹配。
##### 正则表达式
此外，case的判断条件允许是正则表达式。
```
match "hello world":
     /hello(.+)d/ =>
        speak($mg0)
        speak($mg1)        
     "world" =>
        speak("2")
     default =>
        speak("3")
```
输出`hello world`和`  worl`(前面有个空格)
#### 带时间控制的match
这种match的格式是
```
match @()func():
    expr1 =>
        st1
    ...
    silence =>
        stn
```
其中，@()表达式是时间控制表达式，我称它为`at expression`.  
##### @ expression
@()至少要传入一个参数，表示超时的时间。
最多可以传入四个参数，剩下三个分别代表
* 匹配开始时间（最早退出时间）
* 函数超时时间（`func`允许运行的最大时间）
* 睡眠时间（表达式一直在循环判断，可以给一个时间等待，避免浪费计算资源）
一般只需用前两个参数即可
##### 流匹配
和之前的match不同，这里会不断运行函数，产生一个“流”。以listen为例，假设我们在分别输入了`hel`,`lo`.  
内部的结果队列就会形如[`"hel"`,`"lo"`]。每次比较时，把结果队列拼接在一起进行判断。  
第一次是`"hel"`，第二次则为`hello`
##### example
例如:
```
state main:
    @(5,2)listen():
        "stop" =>
            pass
        silence =>
            branch main
```
上面这段代码表示，将会监听`stdin`最多5秒钟，持续匹配结果，同时，最少2s才会给出结果。如果匹配成功，终止运行。  
用字典`Dict[Int,Str]`表示第is输入的字符串。  
那么：
```
{0:"stop"}
{0:"st",2:"op"}
{0:"st",3:"oo",4:"stop"}
```
都是会结束执行的。
而
```
{0:"stoooooooooooop"}
{0:"st",4.9:"o",5:"p"}
```
则会超时，
同时，第一个例子得到2s才会匹配成功，结束程序

## 内置函数

### `listen`

内部实现即`input`。阻塞地从`stdin`中读入一行。

注意，listen可能导致程序**长时间阻塞**。建议搭配`@`表达式使用

### `speak(str)`

内部实现即`print`。在`stdout`中输出一行

### `print(str)`

内部实现为`sys.stderr.write`。在`stderr`中输出一行

### `exit(int)`

内部实现为`sys.exit`。会立刻退出程序。

可以传入一个值表示返回值。默认为0

### `arg_seq_add(name,help_msg)`

添加一个顺序参数。在解释执行中这个函数没有作用。

例如：

```
arg_seq_add("arg1") ## 第一个顺序参数
arg_seq_add("arg2") ## 第二个
```

### `arg_option_add(full_name,short_name,help_msg)`

添加一个可选参数。在解释执行中这个函数没有作用。

```
arg_option_add("option","o") ## --option 或者 -o
```



### `sqlite_connect(db_name)`

连接到sqlite数据库。

`db_name`参数指的是数据库的路径。

会返回一个cursor

```
cursor = sqlite_connect("test.db")
```



### `sqlite(cursor,sql)`

执行一条sql语句。需要带上上面获取的cursor

```
sqlite(cursor,"SELECT * FROM sqlite_master")
```



### `eval(str)`

执行一条简单的python**表达式**。注意是表达式，语句是无法执行的。

默认会传入全局的命名域。

比如：

```
x = 2
x = eval("x**2")
```

这时x=4

使用eval也可以使用`exec`。比如

```
x = 2
x = eval("exec('import math') or math.sqrt(x)")
```

结果是1.414

因此使用eval是有风险的。它可以篡改程序的执行流（当然，它访问不到解释器），因此可能导致程序崩溃。

