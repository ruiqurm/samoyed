# samoyed
[![Documentation Status](https://readthedocs.org/projects/samoyed/badge/?version=latest)](https://samoyed.readthedocs.io/en/latest/?badge=latest)  
`samoyed` 是一个简单的客服机器人DSL。  
文档：https://samoyed.readthedocs.io/en/latest/
## quick start

建立一个文件，名为`exmaple.sam`:

```
state main:
    speak("hello")
	match @(4,2)listen():
		"hello" =>
			speak("hello world")
		silence =>
			speak("超时")

```

可以直接执行：

```
./samc run example.sam 
```

当输入hello的时候，返回`hello world`

当没有输入时，会返回`超时`



也可以将其编译成文件。

```
./samc gen example.sam -o example
```

这会在当前目录下生成：`example`文件

使用`python example`可以执行。



