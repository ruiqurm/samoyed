# import py_compile
import argparse
import os

from samoyed.core import Interpreter

with open("{}/samoyed/compile_template.template".format(os.path.abspath(os.path.dirname(__file__)))) as file:
    template = file.read()


def samoyed_compile(source_file: str, output_file: str) -> None:
    """
    抽出AST，保存到模板文件中。

    Parameters
    ----------
    source_file 源代码文件
    output_file 输出代码的文件
    -------

    """
    with open(source_file, "r", encoding="utf-8") as file:
        src = file.read()
    i = Interpreter(src)
    print(output_file)
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(template.format(pos_arg=i.context.seq_args,
                                   option_arg=i.context.option_args,
                                   ast=i.ast))


parser = argparse.ArgumentParser(
    description='samoyed DSL compiler\n')
parser.add_argument("mode", choices=['run', 'gen'], type=str.lower, help="模式", nargs=1)
parser.add_argument("source", help="要编译的脚本文件", nargs=1)
parser.add_argument("-o", "--output", help="输出文件名", nargs=1)

if __name__ == "__main__":
    args = parser.parse_args()
    if args.mode[0] == "run":
        with open(args.source[0], "r", encoding="utf-8") as f:
            i = Interpreter(f.read())
        i.exec()
    else:
        # mode == gen
        samoyed_compile(args.source[0], args.source[0] + ".py" if args.output is None else args.output[0])
