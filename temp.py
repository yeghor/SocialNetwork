from typing import Literal

t = Literal[10, 20]

def temp(t: t):
    print(t)

temp(10)

temp(t)
temp(30)
