import sys, argparse
from .core import heal

def main():
    p = argparse.ArgumentParser(prog="self-heal")
    p.add_argument("command", nargs="+", help="测试命令, e.g. pytest test.py")
    p.add_argument("--cwd", default=".")
    p.add_argument("--max", type=int, default=3)
    args = p.parse_args()
    result = heal(args.command, args.cwd, args.max)
    if result["success"]:
        print(f"✓ 自愈成功! 尝试了 {result['attempts']} 次")
    else:
        print(f"✗ 未能自愈 ({result['attempts']} 次尝试)")
    sys.exit(0 if result["success"] else 1)

if __name__ == "__main__": main()
