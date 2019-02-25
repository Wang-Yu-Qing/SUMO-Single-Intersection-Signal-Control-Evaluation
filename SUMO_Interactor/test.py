import random
def a():
    return random.randint(1,10)

def test():
    while True:
        yield a()

t = test()
next(t)