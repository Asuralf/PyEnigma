import random


class Transcoder:
    """
        转码器类，因为密码机只运算数字，所以先把字符转换为数字，再输入密码机中运算
        之后把密码机的输出还原为字符。
        只支持 26 个大写字母
    """
    def __init__(self) -> None:
        self.num_range = 26

    def char_to_int(self, char):
        return ord(char) - ord('A')
    
    def int_to_char(self, num):
        return chr(ord('A') + num)


class AsciiTranscoder:
    """
    支持 256 个 ASCII 字符
    """
    def __init__(self) -> None:
        self.num_range = 256 

    def char_to_int(self, char):
        return ord(char)
    
    def int_to_char(self, num):
        return chr(num)


class Enigma:
    """
        enigma 类 具体构造参考附录的原理图
    """
    def __init__(self, transcoder_class=Transcoder, rotor_num=3, rotor_cursors=[], plugboard_pairs={}) -> None:
        """
            args:
                transcoder: Transcoder 类实例，用于转换数字和字符
                roter_num: int 转子数量，默认为3，默认
                roter_cursors: 转子初始位置
                plugboard_pairs: plugboard 交换的字母对 
        """
        self.transcoder = transcoder_class()
        num_range = self.transcoder.num_range

        if not rotor_cursors:
            rotor_cursors = [0 for i in range(rotor_num)]

        self.num_range = num_range
        self.rotor_num = rotor_num
        self.init_cursors = list(rotor_cursors)  # 复制一份
        self.pb = Plugboard(swap_pairs=plugboard_pairs, num_range=num_range)
        self.rotors = [Rotor(cursor=rotor_cursors[i], num_range=num_range) for i in range(rotor_num)]
        self.rf = Reflector(num_range=num_range)

    def reset_cursors(self):
        """
            重置所有转子
        """
        for i in range(self.rotor_num):
            self.rotors[i].set_cursor(self.init_cursors[i])

    def input(self, text):
        """
            加密主要流程
        """
        self.reset_cursors()
        rv = []
        for char in text:
            num = self.transcoder.char_to_int(char)
            num = self.pb.input_num(num)

            for i in range(self.rotor_num):
                num = self.rotors[i].input_num(num)
            
            num = self.rf.input_num(num)

            for i in range(self.rotor_num):
                num = self.rotors[self.rotor_num - 1 - i].input_num_reversed(num)
            
            num = self.pb.input_num(num)
            rv.append(num)

            # 转动转子
            is_rotated = False
            for i in range(self.rotor_num):
                if i == 0:
                    is_rotated = self.rotors[i].rotate()
                else:
                    if is_rotated:
                        is_rotated = self.rotors[i].rotate()
            
        return ''.join([self.transcoder.int_to_char(n) for n in rv])   


class BetterEnigma(Enigma):
    def __init__(self, transcoder_class=Transcoder, rotor_num=3, rotor_cursors=[], plugboard_pairs={}) -> None:
        super().__init__(transcoder_class=transcoder_class, rotor_num=rotor_num, rotor_cursors=rotor_cursors, plugboard_pairs=plugboard_pairs)
        # 一个字母永远不会被加密成它自身，问题出在 reflector
        # 这里采用 BetterReflector 替换
        self.rf = BetterReflector(num_range=self.transcoder.num_range)


class Rotor:

    def __init__(self, scrambled_array=None, cursor=0, num_range=26) -> None:
        """
            Rotor （转子） 的初始化方法
            
            初始化过程中，根据数列生成一个乱序的 scrambled_array = [8, 2, 1, 3, ...]
            或者 scrambled_array 可以由用户提供

            Args:
                scrambled_array: 用户提供的乱序的数列，为 None 则自动随机生成。
                cursor: 为转子的初始位置，应该满足 0 <= cursor < num_range
                num_range: 数字范围
            Raises:
                InvalidScrambledCharsException：输入的 scrambled_array 不正确
                InavlidCursorException: 输入的 cursor 不正确
        """
        if not cursor in range(0, num_range):
            raise self.InvalidCursorException
        self.cursor = int(cursor)

        if scrambled_array:
            # 检查输入是否正确
            sorted_arrary =  sorted(scrambled_array, reverse=False)
            temp_list = list(range(0, num_range))

            if sorted_arrary != temp_list:
                raise self.InvalidScrambledCharsException
        else:
            # 随机生成
            scrambled_array = list(range(0, num_range))
            random.shuffle(scrambled_array)
            
    

        self.num_range = num_range
        self.array = scrambled_array
        self.array_reversed = [-1 for i in range(num_range)]
        for i in range(num_range):
            n = self.array[i]
            self.array_reversed[n] = i

    def input_num(self, num):
        """
            Rotor 输入方法

            Args:
                num: 输入的数字
            returns:
                加密后的数字
        """
        # 加上偏移量 cursor 之后找到下标 index 
        index = (self.cursor + num) % self.num_range
        return self.array[index]
    
    def input_num_reversed(self, num):
        # 相当于 input_num 的逆运算，确保在同样的 cursor 条件下，输入等于输出
        rv = self.array_reversed[num] - self.cursor
        if rv < 0:
            rv += self.num_range
        return rv


    def rotate(self):
        """
            转动转子
            returns:
                tick: 默认为 False，如果转满一周 则为 True
        """
        self.cursor = (self.cursor + 1) % self.num_range
        return self.cursor == 0

    def set_cursor(self, pos):
        self.cursor = pos

    class InvalidScrambledCharsException(Exception):
        pass

    class InvalidCursorException(Exception):
        pass


class Plugboard:
    """
        PlugBoard 类
        交换一些输入的字母，比如交换 A 和 E 后，输入 E 会 输出 A，反之亦然
    """

    def __init__(self, swap_pairs={}, num_range=26):
        """
            Plugboard 初始方法
            Args:
                swap_pairs: 交换的数字对，格式为 {2: 3, 4: 7, 22: 13 ...}
                num_range: 数字范围
        """
        # 验证 swap_pairs
        pairs_reversed = {}
        _range = range(num_range)
        for k, v in swap_pairs.items():
            pairs_reversed[v] = k
            if k not in range(num_range):
                raise self.IvalidSwapPairsException('输入了奇怪的字符')
            if v not in range(num_range):
                raise self.IvalidSwapPairsException('输入了奇怪的字符')
            pairs_reversed[v] = k

        if len(swap_pairs) != len(pairs_reversed):
            raise self.IvalidSwapPairsException('可能存在重复的映射关系')
        
        self.array = list(range(num_range))

        for k, v in swap_pairs.items():
            self.array[k], self.array[v] = v, k
        
        self.num_range = num_range

    def input_num(self, num):
        """
            PlugBoard 输入 num 获得结果
            Args:
                num: int
            Returns:
                转换后的数字
        """
        return self.array[num]

    class IvalidSwapPairsException(Exception):
        pass
        

class Reflector(Plugboard):
    """
        Reflector 反射板，看作有13对交换数字的 Plugboard 
    """
    def __init__(self, num_range=26) -> None:
        random_array = list(range(num_range))
        random.shuffle(random_array)
        swap_pairs = {}
        for i in range(int(num_range / 2)):
            n1 = random_array.pop()
            n2 = random_array.pop()
            swap_pairs[n1] = n2
        return super().__init__(swap_pairs, num_range=num_range)


class BetterReflector(Plugboard):
    """
        BetterReflector 不完全交换所有的字母，只交换一部分 
    """
    def __init__(self, num_range=26) -> None:
        random_array = list(range(num_range))
        random.shuffle(random_array)
        swap_pairs = {}

        # 不去尽量交换所有的字母，而是只交换一部分
        # swap_pairs_num = random.randint(int(num_range / 6), int(num_range / 2))
        swap_pairs_num = int(num_range / 2 * 0.9)
        for i in range(swap_pairs_num):
            n1 = random_array.pop()
            n2 = random_array.pop()
            swap_pairs[n1] = n2
        return super().__init__(swap_pairs, num_range=num_range)



def test_rotor():
    r = Rotor()
    n0 = 12
    n1 = r.input_num(n0)
    n2 = r.input_num_reversed(n1)
    print(n0, n1, n2)
    assert(n0 == n2)

    r.rotate()
    n0 = 12
    n1 = r.input_num(n0)
    n2 = r.input_num_reversed(n1)
    assert(n0 == n2)
    print(n0, n1, n2)
    

def test_plugboard():
    pairs = {1: 3, 2: 4}
    pb = Plugboard(swap_pairs=pairs)
    assert(pb.input_num(0) == 0)
    assert(pb.input_num(4) == 2)
    assert(pb.input_num(1) == 3)
    assert(pb.input_num(3) == 1)


def test_reflector():
    rf = Reflector()
    for i in range(rf.num_range):
        _result = rf.input_num(i)
        _return = rf.input_num(_result)
        assert(i == _return)


def run_test():
    test_rotor()
    test_plugboard()
    test_reflector()


def main():
    # 可以添加任意个转子
    print('-- Enigma -------------')
    enigma = Enigma(rotor_num=5, rotor_cursors=[12, 8, 7, 3, 2], plugboard_pairs={1: 3, 2: 4, 10: 20})
    text = 'HELLOWORLD'
    cipher = enigma.input(text)
    print(cipher)
    plain = enigma.input(cipher)
    print(plain)

    print('---------------')

    text = 'A' * 30
    cipher = enigma.input(text)
    print(cipher)
    plain = enigma.input(cipher)
    print(plain)

    # 一个字母加密后永远不会是它自身
    assert(cipher.find('A') == -1)

    print('-- BetterEnigma -------------')

    be = BetterEnigma()

    text = 'A' * 30
    cipher = be.input(text)
    print(cipher)
    plain = be.input(cipher)
    print(plain)
    # 改进后有时可以是自身
    assert(cipher.find('A') != -1)

    print('-- BetterEnigma in ASCII -------------')

    be = BetterEnigma(transcoder_class=AsciiTranscoder)

    text = ''.join([chr(i) for i in range(ord('A'), ord('z') + 1)]) + '.,?!@#$%^&*()-='
    cipher = be.input(text)
    print(cipher)
    plain = be.input(cipher)
    print(plain)


if __name__ == '__main__':
    # run_test()
    main()
