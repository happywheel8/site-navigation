import re
import sys
from pypinyin import lazy_pinyin

def process_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    words = re.split(',|\n', content)
    words = [word.strip() for word in words if word.strip()]  # 去除每一项前后的空格，如果某一项为空，舍弃它
    words = list(set(words))  # 去重

    a = []  # 存放以汉字开头的项
    b = []  # 存放其它项

    for word in words:
        if '\u4e00' <= word[0] <= '\u9fff':  # 如果word以汉字开头
            a.append(word)
        else:
            b.append(word)

    a.sort(key=lambda word: ''.join(lazy_pinyin(word)))  # a组用拼音排序
    b.sort(key=str.lower)  # b组正常排序，忽略大小写

    c = b + a  # 按照b组在前，a组在后合并成c组

    # 将结果覆盖写入原文件，每行字符数小于或等于40个英文字符，每行包含整数个项
    with open(filename, 'w', encoding='utf-8') as f:
        line = []
        for word in c:
            if len(', '.join(line + [word])) <= 34:  # 如果加上新的项，总字符数仍然小于或等于40
                line.append(word)
            else:  # 否则，先将当前行写入文件，然后开始新的一行
                f.write(', '.join(line) + '\n')
                line = [word]
        if line:  # 如果最后一行还有剩余的项，也写入文件
            f.write(', '.join(line) + '\n')

if __name__ == "__main__":
    process_file(sys.argv[1])
